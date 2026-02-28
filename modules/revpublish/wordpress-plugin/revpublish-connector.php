<?php
/**
 * Plugin Name: RevPublish Connector
 * Plugin URI: https://revflow.os
 * Description: Connects your WordPress site to RevPublish portal for automated content management
 * Version: 1.1.21
 * Author: RevFlow OS
 * Author URI: https://revflow.os
 * License: GPL v2 or later
 * Text Domain: revpublish-connector
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

class RevPublishConnector {
    
    private $portal_url;
    private $site_secret;
    
    public function __construct() {
        $this->portal_url = get_option('revpublish_portal_url', '');
        $this->site_secret = get_option('revpublish_site_secret', '');
        
        // Register REST API endpoint
        add_action('rest_api_init', array($this, 'register_rest_routes'));
        
        // Admin menu
        add_action('admin_menu', array($this, 'add_admin_menu'));
        
        // Auto-register on activation
        register_activation_hook(__FILE__, array($this, 'activate'));
    }
    
    public function register_rest_routes() {
        // Site info endpoint (public, but requires secret)
        register_rest_route('revpublish/v1', '/site-info', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_site_info'),
            'permission_callback' => array($this, 'verify_secret'),
        ));
        
        // Health check endpoint
        register_rest_route('revpublish/v1', '/health', array(
            'methods' => 'GET',
            'callback' => array($this, 'health_check'),
            'permission_callback' => '__return_true',
        ));
        
        // Register with portal endpoint
        register_rest_route('revpublish/v1', '/register', array(
            'methods' => 'POST',
            'callback' => array($this, 'register_with_portal'),
            'permission_callback' => array($this, 'verify_secret'),
        ));

        // Bridge endpoint for updating a specific existing page from RevPublish.
        register_rest_route('revpublish/v1', '/elementor-update', array(
            'methods' => 'POST',
            'callback' => array($this, 'elementor_update_page'),
            'permission_callback' => array($this, 'can_update_page'),
        ));

        // Debug endpoint: inspect selected page Elementor structure for precise mapping.
        register_rest_route('revpublish/v1', '/elementor-structure', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_elementor_structure'),
            'permission_callback' => array($this, 'can_update_page'),
        ));

        // Debug endpoint: return full Elementor JSON for deterministic key mapping.
        register_rest_route('revpublish/v1', '/elementor-json', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_elementor_json'),
            'permission_callback' => array($this, 'can_update_page'),
        ));
    }
    
    public function verify_secret($request) {
        $secret = $request->get_header('X-RevPublish-Secret');
        $stored_secret = get_option('revpublish_site_secret', '');
        
        // If no secret is set, allow first-time access
        if (empty($stored_secret)) {
            return true;
        }
        
        return !empty($secret) && hash_equals($stored_secret, $secret);
    }
    
    public function get_site_info($request) {
        return array(
            'site_id' => get_option('revpublish_site_id', wp_generate_uuid4()),
            'site_name' => get_bloginfo('name'),
            'site_url' => home_url(),
            'admin_url' => admin_url(),
            'wp_version' => get_bloginfo('version'),
            'php_version' => PHP_VERSION,
            'theme' => get_option('stylesheet'),
            'plugins_count' => count(get_option('active_plugins', array())),
            'status' => 'active',
            'registered_at' => get_option('revpublish_registered_at', current_time('mysql')),
            'last_sync' => get_option('revpublish_last_sync', null),
        );
    }
    
    public function health_check($request) {
        return array(
            'status' => 'ok',
            'plugin_version' => '1.1.21',
            'wordpress_version' => get_bloginfo('version'),
            'site_url' => home_url(),
        );
    }

    private function collect_section_summary($elements, &$widget_counts, &$sample_texts) {
        if (!is_array($elements)) {
            return;
        }

        foreach ($elements as $element) {
            if (!is_array($element)) {
                continue;
            }

            $widget_type = isset($element['widgetType']) ? (string) $element['widgetType'] : null;
            if ($widget_type) {
                if (!isset($widget_counts[$widget_type])) {
                    $widget_counts[$widget_type] = 0;
                }
                $widget_counts[$widget_type]++;

                if (isset($element['settings']) && is_array($element['settings'])) {
                    foreach (array('title', 'editor', 'html', 'text', 'description', 'content') as $k) {
                        if (!isset($element['settings'][$k]) || !is_string($element['settings'][$k])) {
                            continue;
                        }
                        $txt = trim((string) wp_strip_all_tags($element['settings'][$k], true));
                        if ($txt === '') {
                            continue;
                        }
                        if (count($sample_texts) < 8) {
                            $sample_texts[] = mb_substr($txt, 0, 120);
                        }
                    }
                }
            }

            if (isset($element['elements']) && is_array($element['elements'])) {
                $this->collect_section_summary($element['elements'], $widget_counts, $sample_texts);
            }
        }
    }

    public function get_elementor_structure($request) {
        $page_id = intval($request->get_param('page_id'));
        if ($page_id <= 0) {
            return new WP_Error('invalid_page_id', 'Valid page_id is required', array('status' => 400));
        }

        $post = get_post($page_id);
        if (!$post) {
            return new WP_Error('page_not_found', 'Target page not found', array('status' => 404));
        }

        $existing_raw = get_post_meta($page_id, '_elementor_data', true);
        $existing_data = null;
        if (is_string($existing_raw) && !empty($existing_raw)) {
            $decoded = json_decode($existing_raw, true);
            if (is_array($decoded)) {
                $existing_data = $decoded;
            }
        }
        if (!is_array($existing_data) || empty($existing_data)) {
            return new WP_Error(
                'missing_existing_layout',
                'No Elementor data found for this page.',
                array('status' => 404)
            );
        }

        $sections = array();
        foreach ($existing_data as $idx => $section) {
            $widget_counts = array();
            $sample_texts = array();
            $elements = (isset($section['elements']) && is_array($section['elements'])) ? $section['elements'] : array();
            $this->collect_section_summary($elements, $widget_counts, $sample_texts);
            $sections[] = array(
                'index' => $idx,
                'id' => isset($section['id']) ? $section['id'] : null,
                'elType' => isset($section['elType']) ? $section['elType'] : null,
                'widget_counts' => $widget_counts,
                'sample_texts' => $sample_texts
            );
        }

        return array(
            'status' => 'success',
            'page_id' => $page_id,
            'page_title' => get_the_title($page_id),
            'plugin_version' => '1.1.21',
            'sections' => $sections
        );
    }

    public function get_elementor_json($request) {
        $page_id = intval($request->get_param('page_id'));
        if ($page_id <= 0) {
            return new WP_Error('invalid_page_id', 'Valid page_id is required', array('status' => 400));
        }

        $post = get_post($page_id);
        if (!$post) {
            return new WP_Error('page_not_found', 'Target page not found', array('status' => 404));
        }

        $existing_raw = get_post_meta($page_id, '_elementor_data', true);
        $existing_data = null;
        if (is_string($existing_raw) && !empty($existing_raw)) {
            $decoded = json_decode($existing_raw, true);
            if (is_array($decoded)) {
                $existing_data = $decoded;
            }
        }
        if (!is_array($existing_data)) {
            return new WP_Error(
                'missing_existing_layout',
                'No Elementor data found for this page.',
                array('status' => 404)
            );
        }

        return array(
            'status' => 'success',
            'page_id' => $page_id,
            'page_title' => get_the_title($page_id),
            'plugin_version' => '1.1.21',
            'elementor_data' => $existing_data,
        );
    }

    private function html_to_clean_lines($html) {
        $html = (string) $html;
        $html = preg_replace('/<\s*br\s*\/?>/i', "\n", $html);
        $html = preg_replace('/<\/(p|div|li|h[1-6]|tr)>/i', "\n", $html);
        $text = wp_strip_all_tags($html, true);
        $text = html_entity_decode($text, ENT_QUOTES | ENT_HTML5, 'UTF-8');
        $text = preg_replace('/\r\n?/', "\n", $text);
        $raw_lines = explode("\n", $text);
        $lines = array();
        foreach ($raw_lines as $line) {
            $line = trim((string) $line);
            if ($line !== '') {
                $lines[] = $line;
            }
        }
        return $lines;
    }

    private function parse_structured_sections($content_html) {
        $raw = (string) $content_html;
        // Preserve line boundaries from HTML blocks before stripping tags.
        $raw = preg_replace('/<\s*br\s*\/?>/i', "\n", $raw);
        $raw = preg_replace('/<\/(p|div|li|h[1-6]|tr)>/i', "\n", $raw);
        $raw = html_entity_decode($raw, ENT_QUOTES | ENT_HTML5, 'UTF-8');
        $raw = wp_strip_all_tags($raw, true);
        $raw = preg_replace('/\r\n?/', "\n", $raw);
        // Force section boundaries even if source text is flattened.
        $raw = preg_replace('/\s*(\d+)(?:\x{FE0F}\x{20E3}|[.)])\s*/u', "\n$1. ", $raw);
        // Force boundaries before common semantic headings from docs.
        $raw = preg_replace(
            '/\s*(Top Bar|Header\s*\/?\s*Navigation|Hero Section|Service Highlights|Detailed Services Section|Team Section|Testimonials?|Latest News|Blog Section|Request A Quote|Contact Section|Footer Section)\b/i',
            "\n$1",
            $raw
        );
        // Force common label boundaries to avoid "Email:...Call:..." collapsing.
        $raw = preg_replace('/\s+([A-Za-z][A-Za-z ]{1,30}:)\s*/', "\n$1 ", $raw);
        $raw = preg_replace('/[ \t]+/', ' ', $raw);
        $raw = preg_replace('/\n+/', "\n", trim((string) $raw));
        $lines = explode("\n", $raw);
        if (empty($lines)) {
            return array();
        }

        $sections = array();
        $current = null;
        $expect_value_after_label = false;

        foreach ($lines as $line) {
            // Section start patterns:
            // 1) "1️⃣ Top Bar ..."
            // 2) "1. Top Bar ..."
            // 3) "1) Top Bar ..."
            // Numbered section must include explicit delimiter (., ), or keycap emoji).
            // This avoids treating phone-like lines (e.g., 765-9000) as section starts.
            if (preg_match('/^\s*(\d+)(?:\x{FE0F}\x{20E3}|[.)])\s+(.+)$/u', $line, $m)) {
                if ($current && !empty($current['values'])) {
                    $sections[] = $current;
                }
                $heading_and_tail = trim((string) $m[2]);
                $title = $heading_and_tail;
                $inline_values = $this->extract_inline_section_values($heading_and_tail, $title);
                $current = array(
                    'index' => intval($m[1]),
                    'title' => $title,
                    'values' => $inline_values,
                );
                $expect_value_after_label = false;
                continue;
            }
            // Semantic section heading (when numbering is absent or flattened).
            if (
                preg_match(
                    '/^(Top Bar|Header\s*\/?\s*Navigation|Hero Section|Service Highlights|Detailed Services Section|Team Section|Testimonials?|Latest News|Blog Section|Request A Quote|Contact Section|Footer Section)\b/i',
                    $line
                )
            ) {
                if ($current && !empty($current['values'])) {
                    $sections[] = $current;
                }
                $current = array(
                    'index' => count($sections) + 1,
                    'title' => trim((string) $line),
                    'values' => array(),
                );
                $expect_value_after_label = false;
                continue;
            }

            if (!$current) {
                continue;
            }

            // Handle label lines like "Email:" then next line as value.
            if (preg_match('/^[^:]{2,60}:$/', $line)) {
                $expect_value_after_label = true;
                continue;
            }

            // Handle inline "Label: value" lines.
            if (preg_match('/^[^:]{2,60}:\s*(.+)$/', $line, $lm)) {
                $tail = trim((string) $lm[1]);
                $parts = preg_split('/\s+(?=[A-Za-z][A-Za-z ]{1,30}:)/', $tail);
                if (!is_array($parts)) {
                    $parts = array($tail);
                }
                foreach ($parts as $part) {
                    $val = preg_replace('/^[^:]{2,60}:\s*/', '', trim((string) $part));
                    if ($val !== '') {
                        $current['values'][] = $val;
                    }
                }
                $expect_value_after_label = false;
                continue;
            }

            // Bullet points.
            $line = preg_replace('/^[•\-\*]+\s*/u', '', $line);
            $line = trim((string) $line);
            if ($line === '') {
                continue;
            }

            if ($expect_value_after_label || $line !== '') {
                $current['values'][] = $line;
                $expect_value_after_label = false;
            }
        }

        if ($current && !empty($current['values'])) {
            $sections[] = $current;
        }

        return $sections;
    }

    private function extract_inline_section_values($text, &$title_out) {
        $text = trim((string) $text);
        $title_out = $text;
        if ($text === '') {
            return array();
        }

        $known_titles = array(
            'Hero Section',
            'About Section',
            'Services Section',
            'Service Highlights',
            'Detailed Services Section',
            'Team Section',
            'Expert Team Section',
            'Projects Section',
            'Testimonials Section',
            'Blog Section',
            'Quote Section',
            'Top Bar',
            'Header / Navigation CTA',
        );

        $tail = '';
        foreach ($known_titles as $kt) {
            if (stripos($text, $kt) === 0) {
                $title_out = $kt;
                $tail = trim((string) substr($text, strlen($kt)));
                break;
            }
        }
        if ($tail === '') {
            // Generic fallback: split at first label marker.
            if (preg_match('/^(.{2,80}?)(\s+[A-Za-z][A-Za-z0-9 \/\-&]{1,35}:\s+.*)$/', $text, $mm)) {
                $title_out = trim((string) $mm[1]);
                $tail = trim((string) $mm[2]);
            }
        }

        if ($tail === '') {
            return array();
        }

        $parts = preg_split('/\s+(?=[A-Za-z][A-Za-z0-9 \/\-&]{1,35}:)/', $tail);
        if (!is_array($parts)) {
            $parts = array($tail);
        }
        $values = array();
        foreach ($parts as $part) {
            $part = trim((string) $part);
            if ($part === '') {
                continue;
            }
            // Remove "Label:" prefix if present.
            $value = preg_replace('/^[A-Za-z][A-Za-z0-9 \/\-&]{1,35}:\s*/', '', $part);
            $value = $this->clean_candidate_value($value);
            if ($value !== '') {
                $values[] = $value;
            }
        }
        return $values;
    }

    public function can_update_page($request) {
        // Preferred auth for server-to-site updates: WordPress Application Password / logged-in admin user.
        if (current_user_can('edit_pages')) {
            return true;
        }

        // Optional auth path for secret-based connector mode.
        return $this->verify_secret($request);
    }

    private function split_content_sections($html) {
        $html = trim((string) $html);
        if ($html === '') {
            return array();
        }

        // Split by headings while keeping headings in output chunks.
        $parts = preg_split('/(<h[1-6][^>]*>.*?<\/h[1-6]>)/is', $html, -1, PREG_SPLIT_DELIM_CAPTURE | PREG_SPLIT_NO_EMPTY);
        if (!is_array($parts) || empty($parts)) {
            return array($html);
        }

        $sections = array();
        $buffer = '';
        foreach ($parts as $part) {
            if (preg_match('/^<h[1-6][^>]*>.*?<\/h[1-6]>$/is', $part)) {
                if (trim($buffer) !== '') {
                    $sections[] = trim($buffer);
                }
                $buffer = $part;
            } else {
                $buffer .= $part;
            }
        }
        if (trim($buffer) !== '') {
            $sections[] = trim($buffer);
        }

        return !empty($sections) ? $sections : array($html);
    }

    private function get_allowed_setting_keys_for_widget($widget_type, $allow_heading_like) {
        // Keep this conservative to avoid breaking visual structure.
        // For first/hero section we avoid replacing heading-like keys.
        if ($widget_type === 'text-editor') {
            return array('editor');
        }
        if ($widget_type === 'html') {
            return array('html');
        }
        if ($widget_type === 'button') {
            return array('text', 'button_text');
        }
        if ($widget_type === 'section-title') {
            $keys = array('description');
            if ($allow_heading_like) {
                $keys = array_merge($keys, array('subtitle', 'title', 'title_two', 'highlight_text'));
            }
            return $keys;
        }
        if ($widget_type === 'iconbox') {
            return array('title_text', 'description_text');
        }
        if ($widget_type === 'service') {
            return array('title_text', 'title_tex_two', 'description_text', 'button_text');
        }
        if ($widget_type === 'team') {
            return array('team_name', 'team_designation');
        }
        if ($widget_type === 'dreamit-counter') {
            return array('title', 'number', 'suffix');
        }
        if ($widget_type === 'dit-button') {
            return array('button_text');
        }
        if ($widget_type === 'blogpost') {
            return array('button_text');
        }
        if ($widget_type === 'slider' || $widget_type === 'testimonial') {
            // These widgets keep content inside repeater arrays; use heuristic text slot detection.
            return array('*');
        }
        // Generic content-bearing keys in many widgets.
        $keys = array('description', 'content');
        if ($allow_heading_like) {
            $keys = array_merge($keys, array('title', 'subtitle', 'title_text', 'description_text', 'text'));
        }
        return $keys;
    }

    private function is_probable_text_key($key) {
        $key = strtolower((string) $key);
        if ($key === '') {
            return false;
        }
        $blacklist = array('img', 'image', 'icon', 'url', 'link', 'class', 'id', 'style', 'color', 'size');
        foreach ($blacklist as $bad) {
            if (strpos($key, $bad) !== false) {
                return false;
            }
        }
        $whitelist = array('title', 'text', 'desc', 'content', 'name', 'designation', 'label', 'caption', 'subtitle', 'button');
        foreach ($whitelist as $ok) {
            if (strpos($key, $ok) !== false) {
                return true;
            }
        }
        return false;
    }

    private function normalize_section_for_key($section, $setting_key) {
        $section = (string) $section;
        $key = (string) $setting_key;

        if ($key === 'editor' || $key === 'html' || $key === 'content') {
            return $section;
        }

        // For description-like keys, keep plain text to avoid malformed UI.
        $plain = wp_strip_all_tags($section, true);
        $plain = preg_replace('/\s+/', ' ', $plain);
        return trim((string) $plain);
    }

    private function clean_candidate_value($value) {
        $v = trim((string) $value);
        // Drop bare numbering/noise tokens generated by flattened docs parsing.
        if (preg_match('/^\d+[.)]?$/', $v)) {
            return '';
        }
        $v = preg_replace('/^[•\-\*]+\s*/u', '', $v);
        $v = trim((string) $v);
        return $v;
    }

    private function key_wants_short_value($setting_key) {
        $k = strtolower((string) $setting_key);
        foreach (array('title', 'name', 'subtitle', 'button', 'designation') as $m) {
            if (strpos($k, $m) !== false) {
                return true;
            }
        }
        return false;
    }

    private function key_wants_numeric_value($setting_key) {
        $k = strtolower((string) $setting_key);
        return $k === 'number' || strpos($k, 'count') !== false;
    }

    private function pick_next_value_for_key($sections, &$section_index, $setting_key) {
        if (empty($sections) || $section_index >= count($sections)) {
            return null;
        }
        $want_short = $this->key_wants_short_value($setting_key);
        $want_numeric = $this->key_wants_numeric_value($setting_key);

        for ($i = $section_index; $i < count($sections); $i++) {
            $candidate = $this->clean_candidate_value($sections[$i]);
            if ($candidate === '') {
                continue;
            }

            if ($want_numeric) {
                if (!preg_match('/^\d+[+]?$|^\d[\d,\. ]*[+]?$/', $candidate)) {
                    continue;
                }
            } elseif ($want_short) {
                // Keep short UI labels concise; avoid dumping long paragraphs into title fields.
                if (mb_strlen(wp_strip_all_tags($candidate, true)) > 90) {
                    continue;
                }
            }

            $section_index = $i + 1;
            return $candidate;
        }

        return null;
    }

    private function replace_text_slots_in_settings(&$settings, $sections, &$section_index, &$found_count, &$assigned_count, $allowed_keys) {
        if (!is_array($settings)) {
            return;
        }

        foreach ($settings as $k => &$v) {
            if (is_array($v)) {
                $this->replace_text_slots_in_settings($v, $sections, $section_index, $found_count, $assigned_count, $allowed_keys);
                continue;
            }

            if (!is_string($v)) {
                continue;
            }

            $key_allowed = in_array((string) $k, $allowed_keys, true);
            if (!$key_allowed && in_array('*', $allowed_keys, true)) {
                $key_allowed = $this->is_probable_text_key((string) $k);
            }
            if (!$key_allowed) {
                continue;
            }

            $found_count++;
            $has_sections = !empty($sections);
            if ($has_sections && $section_index < count($sections)) {
                $selected = $this->pick_next_value_for_key($sections, $section_index, (string) $k);
                if ($selected !== null && $selected !== '') {
                    $v = $this->normalize_section_for_key($selected, (string) $k);
                    $assigned_count++;
                }
            }
            // If no section left, keep existing value to protect layout integrity.
        }
    }

    private function update_rich_text_widgets_sequential(&$elements, $sections, &$section_index, &$found_count, &$assigned_count, $allow_heading_like) {
        if (!is_array($elements)) {
            return;
        }

        foreach ($elements as &$element) {
            if (
                isset($element['settings']) &&
                is_array($element['settings'])
            ) {
                $widget_type = isset($element['widgetType']) ? (string) $element['widgetType'] : '';
                $allowed_keys = $this->get_allowed_setting_keys_for_widget($widget_type, $allow_heading_like);
                $this->replace_text_slots_in_settings(
                    $element['settings'],
                    $sections,
                    $section_index,
                    $found_count,
                    $assigned_count,
                    $allowed_keys
                );
            }

            if (isset($element['elements']) && is_array($element['elements'])) {
                $this->update_rich_text_widgets_sequential($element['elements'], $sections, $section_index, $found_count, $assigned_count, $allow_heading_like);
            }
        }
    }

    private function flatten_structured_values($structured_sections) {
        $values = array();
        foreach ($structured_sections as $section) {
            if (!isset($section['values']) || !is_array($section['values'])) {
                continue;
            }
            foreach ($section['values'] as $v) {
                $v = trim((string) $v);
                if ($v !== '') {
                    $values[] = $v;
                }
            }
        }
        return $values;
    }

    private function normalize_section_title_key($title) {
        $t = strtolower(trim((string) $title));
        if ($t === '') {
            return '';
        }
        if (strpos($t, 'top bar') !== false || strpos($t, 'topbar') !== false) {
            return 'top_bar';
        }
        if (strpos($t, 'hero') !== false || strpos($t, 'banner') !== false) {
            return 'hero';
        }
        if (strpos($t, 'about') !== false) {
            return 'about';
        }
        if (strpos($t, 'team') !== false || strpos($t, 'expert') !== false) {
            return 'team';
        }
        if (strpos($t, 'testimonial') !== false || strpos($t, 'review') !== false) {
            return 'testimonials';
        }
        if (strpos($t, 'stat') !== false || strpos($t, 'counter') !== false || strpos($t, 'number') !== false) {
            return 'stats';
        }
        if (strpos($t, 'project') !== false || strpos($t, 'portfolio') !== false) {
            return 'projects';
        }
        if (strpos($t, 'blog') !== false || strpos($t, 'news') !== false) {
            return 'blog';
        }
        if (strpos($t, 'cta') !== false || strpos($t, 'call to action') !== false) {
            return 'cta';
        }
        if (strpos($t, 'quote section') !== false || strpos($t, 'quote') !== false) {
            return 'cta';
        }
        if (strpos($t, 'service') !== false) {
            if (strpos($t, 'service highlights') !== false) {
                return 'about';
            }
            return 'services';
        }
        if (strpos($t, 'detail') !== false && strpos($t, 'service') !== false) {
            return 'services';
        }
        if (strpos($t, 'request a quote') !== false || strpos($t, 'contact section') !== false) {
            return 'cta';
        }
        return preg_replace('/[^a-z0-9]+/', '_', $t);
    }

    private function build_structured_value_map($structured_sections) {
        $map = array();
        foreach ($structured_sections as $section) {
            if (!is_array($section)) {
                continue;
            }
            $values = isset($section['values']) && is_array($section['values']) ? $section['values'] : array();
            if (empty($values)) {
                continue;
            }
            $key = $this->normalize_section_title_key(isset($section['title']) ? $section['title'] : '');
            if ($key === '') {
                continue;
            }
            // Ignore noisy unknown numeric headings (e.g., "765_9000right").
            if (preg_match('/^\d/', $key)) {
                continue;
            }
            if (!isset($map[$key])) {
                $map[$key] = array();
            }
            $clean_values = array();
            foreach ($values as $raw_value) {
                $cv = $this->clean_candidate_value($raw_value);
                if ($cv !== '') {
                    $clean_values[] = $cv;
                }
            }
            if (!empty($clean_values)) {
                $map[$key] = array_values(array_unique(array_merge($map[$key], $clean_values)));
            }
        }
        return $map;
    }

    private function detect_section_key_from_widgets($widget_counts, $section_index) {
        if (isset($widget_counts['slider']) && $widget_counts['slider'] > 0) {
            return 'hero';
        }
        if (isset($widget_counts['service']) && $widget_counts['service'] > 0) {
            return 'services';
        }
        if (isset($widget_counts['team']) && $widget_counts['team'] > 0) {
            return 'team';
        }
        if (isset($widget_counts['testimonial']) && $widget_counts['testimonial'] > 0) {
            return 'testimonials';
        }
        if (isset($widget_counts['dreamit-counter']) && $widget_counts['dreamit-counter'] > 0) {
            return 'stats';
        }
        if (isset($widget_counts['blogpost']) && $widget_counts['blogpost'] > 0) {
            return 'blog';
        }
        if (isset($widget_counts['casestudy']) && $widget_counts['casestudy'] > 0) {
            return 'projects';
        }
        if ($section_index === 4 && isset($widget_counts['section-title']) && $widget_counts['section-title'] > 0) {
            return 'projects';
        }
        if ($section_index === 1 && isset($widget_counts['iconbox']) && $widget_counts['iconbox'] > 0) {
            return 'about';
        }
        if ($section_index === 8 && isset($widget_counts['section-title']) && $widget_counts['section-title'] > 0) {
            return 'cta';
        }
        if ($section_index === 0) {
            return 'hero';
        }
        return '';
    }

    private function normalize_label_key($label) {
        $k = strtolower(trim((string) $label));
        $k = preg_replace('/\s+/', ' ', $k);
        return $k;
    }

    private function split_heading_and_tail_for_labels($heading_text) {
        $heading_text = trim((string) $heading_text);
        $known_titles = array(
            'Hero Section',
            'About + Highlights Section',
            'About Section',
            'Services Section',
            'Team Section',
            'Projects Section',
            'Testimonials + Counters Section',
            'Testimonials Section',
            'Blog Section',
            'Quote Section',
        );
        foreach ($known_titles as $title) {
            if (stripos($heading_text, $title) === 0) {
                $tail = trim((string) substr($heading_text, strlen($title)));
                return array($title, $tail);
            }
        }
        if (preg_match('/^(.{2,100}?)(\s+[A-Za-z][A-Za-z0-9 \/\+\-&]{1,40}:\s+.*)$/', $heading_text, $m)) {
            return array(trim((string) $m[1]), trim((string) $m[2]));
        }
        return array($heading_text, '');
    }

    private function extract_labels_from_text($text) {
        $text = trim((string) $text);
        if ($text === '') {
            return array();
        }
        // Split where a new "Label:" starts.
        $parts = preg_split('/\s+(?=[A-Za-z][A-Za-z0-9 \/\+\-&]{1,40}:)/', $text);
        if (!is_array($parts)) {
            $parts = array($text);
        }
        $pairs = array();
        foreach ($parts as $part) {
            $part = trim((string) $part);
            if ($part === '') {
                continue;
            }
            if (!preg_match('/^([A-Za-z][A-Za-z0-9 \/\+\-&]{1,40}):\s*(.*)$/', $part, $m)) {
                continue;
            }
            $label = $this->normalize_label_key($m[1]);
            $value = $this->clean_candidate_value($m[2]);
            if ($label !== '') {
                $pairs[] = array($label, $value);
            }
        }
        return $pairs;
    }

    private function parse_labeled_sections_map($content_html) {
        $raw = (string) $content_html;
        $raw = preg_replace('/<\s*br\s*\/?>/i', "\n", $raw);
        $raw = preg_replace('/<\/(p|div|li|h[1-6]|tr)>/i', "\n", $raw);
        $raw = html_entity_decode($raw, ENT_QUOTES | ENT_HTML5, 'UTF-8');
        $raw = wp_strip_all_tags($raw, true);
        $raw = preg_replace('/\r\n?/', "\n", $raw);
        // Ensure numbered sections are split even if merged in one line.
        $raw = preg_replace('/\s+(\d+\s*[.)]\s+)/u', "\n$1", $raw);
        // Ensure semantic headings also split when merged.
        $raw = preg_replace(
            '/\s+(Hero Section|About Section|About \+ Highlights Section|Services Section|Team Section|Projects Section|Testimonials \+ Counters Section|Testimonials Section|Blog Section|Quote Section)\b/i',
            "\n$1",
            $raw
        );
        $raw = preg_replace('/[ \t]+/', ' ', $raw);
        $raw = preg_replace('/\n+/', "\n", trim((string) $raw));
        $lines = explode("\n", $raw);
        $map = array();
        $current_section = '';
        foreach ($lines as $line) {
            $line = trim((string) $line);
            if ($line === '') {
                continue;
            }
            // Strict numbered section headings.
            if (preg_match('/^\s*\d+\s*[.)]\s*(.+)$/u', $line, $m)) {
                list($heading_title, $heading_tail) = $this->split_heading_and_tail_for_labels($m[1]);
                $current_section = $this->normalize_section_title_key(trim((string) $heading_title));
                if ($current_section !== '' && !isset($map[$current_section])) {
                    $map[$current_section] = array();
                }
                if ($current_section !== '' && $heading_tail !== '') {
                    $pairs = $this->extract_labels_from_text($heading_tail);
                    foreach ($pairs as $pair) {
                        $map[$current_section][$pair[0]] = $pair[1];
                    }
                }
                continue;
            }
            // Semantic section headings.
            if (
                preg_match(
                    '/^(Hero Section|About Section|About \+ Highlights Section|Services Section|Team Section|Projects Section|Testimonials \+ Counters Section|Testimonials Section|Blog Section|Quote Section)\b/i',
                    $line
                )
            ) {
                list($heading_title, $heading_tail) = $this->split_heading_and_tail_for_labels($line);
                $current_section = $this->normalize_section_title_key($heading_title);
                if ($current_section !== '' && !isset($map[$current_section])) {
                    $map[$current_section] = array();
                }
                if ($current_section !== '' && $heading_tail !== '') {
                    $pairs = $this->extract_labels_from_text($heading_tail);
                    foreach ($pairs as $pair) {
                        $map[$current_section][$pair[0]] = $pair[1];
                    }
                }
                continue;
            }
            if ($current_section === '') {
                continue;
            }
            $pairs = $this->extract_labels_from_text($line);
            foreach ($pairs as $pair) {
                $map[$current_section][$pair[0]] = $pair[1];
            }
        }
        return $map;
    }

    private function getv($arr, $key, $default = '') {
        if (!is_array($arr)) {
            return $default;
        }
        if (isset($arr[$key]) && (string) $arr[$key] !== '') {
            return (string) $arr[$key];
        }
        $want = $this->normalize_label_key($key);
        $want_compact = preg_replace('/[^a-z0-9]+/', '', $want);
        $want_without_prefix = preg_replace('/^(hero|about|services|team|projects|testimonials|blog|quote|cta)\s+/', '', $want);
        $want_without_prefix_compact = preg_replace('/[^a-z0-9]+/', '', $want_without_prefix);

        foreach ($arr as $k => $v) {
            $vv = (string) $v;
            if ($vv === '') {
                continue;
            }
            $kk = $this->normalize_label_key((string) $k);
            $kk_compact = preg_replace('/[^a-z0-9]+/', '', $kk);
            if ($kk === $want || $kk_compact === $want_compact) {
                return $vv;
            }
            if ($want_without_prefix !== '' && ($kk === $want_without_prefix || $kk_compact === $want_without_prefix_compact)) {
                return $vv;
            }
            // Fallback contains checks for merged/flattened labels.
            if (
                strpos($kk, $want) !== false ||
                strpos($kk, $want_without_prefix) !== false ||
                strpos($want, $kk) !== false ||
                ($want_without_prefix !== '' && strpos($want_without_prefix, $kk) !== false)
            ) {
                return $vv;
            }
        }
        return $default;
    }

    private function apply_home03_labeled_mapping(&$existing_data, $labeled_map, &$found_text_widgets, &$updated_widgets, &$mapping_debug) {
        if (!is_array($existing_data) || empty($existing_data) || !is_array($labeled_map) || empty($labeled_map)) {
            return;
        }
        // This deterministic mapper targets the known home-03 section layout.
        foreach ($existing_data as $sec_index => &$section_block) {
            if (!is_array($section_block) || !isset($section_block['elements']) || !is_array($section_block['elements'])) {
                continue;
            }
            $widget_counts = array();
            $sample_texts = array();
            $this->collect_section_summary($section_block['elements'], $widget_counts, $sample_texts);
            $section_key = $this->detect_section_key_from_widgets($widget_counts, $sec_index);
            if ($section_key === '' || !isset($labeled_map[$section_key])) {
                continue;
            }
            $L = $labeled_map[$section_key];
            $mapping_debug['labeled_keys'][] = $section_key;

            $walker = function (&$elements) use (&$walker, $section_key, $L, &$found_text_widgets, &$updated_widgets) {
                if (!is_array($elements)) {
                    return;
                }
                foreach ($elements as &$element) {
                    if (isset($element['settings']) && is_array($element['settings'])) {
                        $wt = isset($element['widgetType']) ? (string) $element['widgetType'] : '';
                        $s =& $element['settings'];

                        if ($section_key === 'hero' && $wt === 'slider' && isset($s['list']) && is_array($s['list']) && !empty($s['list']) && is_array($s['list'][0])) {
                            $sl =& $s['list'][0];
                            $pairs = array(
                                'hero subtitle' => 'subtitle',
                                'hero heading' => 'title',
                                'hero description' => 'description',
                                'hero button' => 'btn1',
                                'hero shape subtitle' => 'shape_subtitle',
                                'hero shape number' => 'shape_title',
                            );
                            foreach ($pairs as $label => $target_key) {
                                $found_text_widgets++;
                                $v = $this->getv($L, $label, '');
                                if ($v !== '') {
                                    $sl[$target_key] = $this->normalize_section_for_key($v, $target_key);
                                    $updated_widgets++;
                                }
                            }
                        }

                        if ($wt === 'section-title') {
                            $mapBySection = array(
                                'about' => array('about small label' => 'subtitle', 'about main heading' => 'title', 'about secondary heading' => 'title_two', 'about paragraph' => 'description'),
                                'services' => array('services small label' => 'subtitle', 'services main heading' => 'title', 'services secondary heading' => 'title_two', 'services intro paragraph' => 'description'),
                                'team' => array('team small label' => 'subtitle', 'team main heading' => 'title', 'team secondary heading' => 'title_two', 'team paragraph' => 'description'),
                                'projects' => array('projects small label' => 'subtitle', 'projects main heading' => 'title', 'projects secondary heading' => 'title_two', 'projects paragraph' => 'description'),
                                'testimonials' => array('testimonials small label' => 'subtitle', 'testimonials main heading' => 'title', 'testimonials secondary heading' => 'title_two', 'testimonials paragraph' => 'description'),
                                'blog' => array('blog small label' => 'subtitle', 'blog main heading' => 'title', 'blog paragraph' => 'description'),
                                'cta' => array('quote small label' => 'subtitle', 'quote main heading' => 'title'),
                            );
                            if (isset($mapBySection[$section_key])) {
                                foreach ($mapBySection[$section_key] as $label => $key) {
                                    $found_text_widgets++;
                                    $v = $this->getv($L, $label, '');
                                    if ($v !== '') {
                                        $s[$key] = $this->normalize_section_for_key($v, $key);
                                        $updated_widgets++;
                                    }
                                }
                            }
                        }

                        if ($section_key === 'about' && $wt === 'iconbox') {
                            static $aboutIdx = 0;
                            $aboutIdx++;
                            $titleLabel = $aboutIdx <= 3 ? "highlight {$aboutIdx} title" : "feature " . ($aboutIdx - 3) . " title";
                            $descLabel = $aboutIdx <= 3 ? "highlight {$aboutIdx} description" : "feature " . ($aboutIdx - 3) . " description";
                            foreach (array($titleLabel => 'title_text', $descLabel => 'description_text') as $label => $key) {
                                $found_text_widgets++;
                                $v = $this->getv($L, $label, '');
                                if ($v !== '') {
                                    $s[$key] = $this->normalize_section_for_key($v, $key);
                                    $updated_widgets++;
                                }
                            }
                        }

                        if ($section_key === 'services' && $wt === 'service') {
                            static $svcIdx = 0;
                            $svcIdx++;
                            foreach (array("service {$svcIdx} title" => 'title_text', "service {$svcIdx} description" => 'description_text') as $label => $key) {
                                $found_text_widgets++;
                                $v = $this->getv($L, $label, '');
                                if ($v !== '') {
                                    $s[$key] = $this->normalize_section_for_key($v, $key);
                                    $updated_widgets++;
                                }
                            }
                        }

                        if ($section_key === 'team' && $wt === 'team') {
                            static $teamIdx = 0;
                            $teamIdx++;
                            foreach (array("member {$teamIdx} name" => 'team_name', "member {$teamIdx} role" => 'team_designation') as $label => $key) {
                                $found_text_widgets++;
                                $v = $this->getv($L, $label, '');
                                if ($v !== '') {
                                    $s[$key] = $this->normalize_section_for_key($v, $key);
                                    $updated_widgets++;
                                }
                            }
                        }

                        if ($section_key === 'testimonials' && $wt === 'testimonial' && isset($s['slides']) && is_array($s['slides'])) {
                            for ($i = 0; $i < count($s['slides']) && $i < 3; $i++) {
                                if (!is_array($s['slides'][$i])) {
                                    continue;
                                }
                                $n = $i + 1;
                                $slidePairs = array(
                                    "testimonial {$n} name" => 'name',
                                    "testimonial {$n} role" => 'designation',
                                    "testimonial {$n} text" => 'quote_text',
                                );
                                foreach ($slidePairs as $label => $key) {
                                    $found_text_widgets++;
                                    $v = $this->getv($L, $label, '');
                                    if ($v !== '') {
                                        $s['slides'][$i][$key] = $this->normalize_section_for_key($v, $key);
                                        $updated_widgets++;
                                    }
                                }
                            }
                        }

                        if ($section_key === 'testimonials' && $wt === 'dreamit-counter') {
                            static $counterIdx = 0;
                            $counterIdx++;
                            foreach (array("counter {$counterIdx} number" => 'number', "counter {$counterIdx} suffix" => 'suffix', "counter {$counterIdx} label" => 'title') as $label => $key) {
                                $found_text_widgets++;
                                $v = $this->getv($L, $label, '');
                                if ($v !== '') {
                                    $s[$key] = $this->normalize_section_for_key($v, $key);
                                    $updated_widgets++;
                                }
                            }
                        }

                        if ($section_key === 'blog' && $wt === 'blogpost') {
                            $found_text_widgets++;
                            $v = $this->getv($L, 'blog button', '');
                            if ($v !== '') {
                                $s['button_text'] = $this->normalize_section_for_key($v, 'button_text');
                                $updated_widgets++;
                            }
                        }

                        if (($section_key === 'about' || $section_key === 'services') && $wt === 'dit-button') {
                            $label = $section_key === 'about' ? 'about button' : 'services button';
                            $found_text_widgets++;
                            $v = $this->getv($L, $label, '');
                            if ($v !== '') {
                                $s['button_text'] = $this->normalize_section_for_key($v, 'button_text');
                                $updated_widgets++;
                            }
                        }
                    }
                    if (isset($element['elements']) && is_array($element['elements'])) {
                        $walker($element['elements']);
                    }
                }
            };
            $walker($section_block['elements']);
        }
        unset($section_block);
    }

    private function get_widget_keys_for_section($widget_type, $section_key) {
        if ($widget_type === 'slider') {
            return ($section_key === 'hero')
                ? array('subtitle', 'title', 'title_two', 'description', 'btn1', 'shape_subtitle', 'shape_title')
                : array();
        }
        if ($widget_type === 'section-title') {
            if ($section_key === 'hero') {
                return array();
            }
            return array('subtitle', 'title', 'title_two', 'description');
        }
        if ($widget_type === 'iconbox' && $section_key === 'about') {
            return array('title_text', 'description_text');
        }
        if ($widget_type === 'service' && $section_key === 'services') {
            return array('title_text', 'title_tex_two', 'description_text');
        }
        if ($widget_type === 'team' && $section_key === 'team') {
            return array('team_name', 'team_designation');
        }
        if ($widget_type === 'testimonial' && $section_key === 'testimonials') {
            return array('title', 'name', 'designation', 'description', 'text', 'content');
        }
        if ($widget_type === 'dreamit-counter' && ($section_key === 'testimonials' || $section_key === 'stats')) {
            return array('number', 'suffix', 'title');
        }
        if ($widget_type === 'blogpost' && $section_key === 'blog') {
            return array('button_text');
        }
        return array();
    }

    private function apply_structured_mapping_to_elements(&$elements, $section_key, $values, &$value_index, &$found_count, &$assigned_count) {
        if (!is_array($elements)) {
            return;
        }

        foreach ($elements as &$element) {
            if (isset($element['settings']) && is_array($element['settings'])) {
                $widget_type = isset($element['widgetType']) ? (string) $element['widgetType'] : '';
                $allowed_keys = $this->get_widget_keys_for_section($widget_type, $section_key);
                if (!empty($allowed_keys)) {
                    $this->replace_text_slots_in_settings(
                        $element['settings'],
                        $values,
                        $value_index,
                        $found_count,
                        $assigned_count,
                        $allowed_keys
                    );
                }
            }
            if (isset($element['elements']) && is_array($element['elements'])) {
                $this->apply_structured_mapping_to_elements(
                    $element['elements'],
                    $section_key,
                    $values,
                    $value_index,
                    $found_count,
                    $assigned_count
                );
            }
        }
    }

    private function append_text_editor_to_first_column(&$elements, $html, &$appended) {
        if (!is_array($elements) || $appended) {
            return;
        }

        foreach ($elements as &$element) {
            if ($appended) {
                return;
            }

            if (
                isset($element['elType']) &&
                $element['elType'] === 'column' &&
                isset($element['elements']) &&
                is_array($element['elements'])
            ) {
                $element['elements'][] = array(
                    'id' => 'revpublish-inline-content-' . wp_generate_password(8, false, false),
                    'elType' => 'widget',
                    'widgetType' => 'text-editor',
                    'settings' => array(
                        'editor' => $html,
                    ),
                );
                $appended = true;
                return;
            }

            if (isset($element['elements']) && is_array($element['elements'])) {
                $this->append_text_editor_to_first_column($element['elements'], $html, $appended);
            }
        }
    }

    private function update_first_heading(&$elements, $title, &$updated) {
        if (!is_array($elements) || empty($title)) {
            return;
        }

        foreach ($elements as &$element) {
            if ($updated) {
                return;
            }

            if (
                isset($element['widgetType']) &&
                $element['widgetType'] === 'heading' &&
                isset($element['settings']) &&
                is_array($element['settings']) &&
                isset($element['settings']['title'])
            ) {
                $element['settings']['title'] = $title;
                $updated = true;
                return;
            }

            if (isset($element['elements']) && is_array($element['elements'])) {
                $this->update_first_heading($element['elements'], $title, $updated);
            }
        }
    }

    private function build_basic_elementor_data($title, $html) {
        return array(
            array(
                'id' => 'revpublish-section-' . wp_generate_password(8, false, false),
                'elType' => 'section',
                'settings' => new stdClass(),
                'elements' => array(
                    array(
                        'id' => 'revpublish-column-' . wp_generate_password(8, false, false),
                        'elType' => 'column',
                        'settings' => new stdClass(),
                        'elements' => array(
                            array(
                                'id' => 'revpublish-heading-' . wp_generate_password(8, false, false),
                                'elType' => 'widget',
                                'widgetType' => 'heading',
                                'settings' => array(
                                    'title' => $title,
                                    'header_size' => 'h1',
                                ),
                            ),
                            array(
                                'id' => 'revpublish-content-' . wp_generate_password(8, false, false),
                                'elType' => 'widget',
                                'widgetType' => 'text-editor',
                                'settings' => array(
                                    'editor' => $html,
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        );
    }

    public function elementor_update_page($request) {
        $params = $request->get_json_params();
        if (!is_array($params)) {
            $params = $request->get_params();
        }

        $page_id = isset($params['page_id']) ? intval($params['page_id']) : 0;
        $title = isset($params['title']) ? sanitize_text_field($params['title']) : '';
        $content_html = isset($params['content_html']) ? wp_kses_post($params['content_html']) : '';
        $elementor_data_override = isset($params['elementor_data_override']) ? $params['elementor_data_override'] : null;
        if (is_string($elementor_data_override) && !empty($elementor_data_override)) {
            $decoded_override = json_decode($elementor_data_override, true);
            if (is_array($decoded_override)) {
                $elementor_data_override = $decoded_override;
            }
        }
        $status = isset($params['status']) ? sanitize_key($params['status']) : '';
        $preserve_layout = true;
        $allow_title_update = false;
        $replace_existing_text_only = true;
        $strict_labeled_mapping = true;
        if (isset($params['preserve_layout'])) {
            $preserve_layout = filter_var($params['preserve_layout'], FILTER_VALIDATE_BOOLEAN);
        }
        if (isset($params['allow_title_update'])) {
            $allow_title_update = filter_var($params['allow_title_update'], FILTER_VALIDATE_BOOLEAN);
        }
        if (isset($params['replace_existing_text_only'])) {
            $replace_existing_text_only = filter_var($params['replace_existing_text_only'], FILTER_VALIDATE_BOOLEAN);
        }
        if (isset($params['strict_labeled_mapping'])) {
            $strict_labeled_mapping = filter_var($params['strict_labeled_mapping'], FILTER_VALIDATE_BOOLEAN);
        }

        if ($page_id <= 0) {
            return new WP_Error('invalid_page_id', 'Valid page_id is required', array('status' => 400));
        }
        if (empty($content_html) && !is_array($elementor_data_override)) {
            return new WP_Error('missing_content', 'content_html is required', array('status' => 400));
        }

        $post = get_post($page_id);
        if (!$post) {
            return new WP_Error('page_not_found', 'Target page not found', array('status' => 404));
        }

        $allowed_statuses = array('draft', 'publish', 'pending', 'private');
        if (!in_array($status, $allowed_statuses, true)) {
            $status = $post->post_status;
        }

        $update_args = array(
            'ID' => $page_id,
            'post_status' => $status,
        );
        // In preserve-layout mode, avoid writing raw imported text into post_content.
        // Some themes render post_content above Elementor canvas, causing banner/top overlap.
        if (!$preserve_layout) {
            $update_args['post_content'] = $content_html;
        }
        if ($allow_title_update && !empty($title)) {
            $update_args['post_title'] = $title;
        }

        $updated_id = wp_update_post($update_args, true);
        if (is_wp_error($updated_id)) {
            return new WP_Error('update_failed', $updated_id->get_error_message(), array('status' => 500));
        }

        // Keep/update Elementor data so page remains editable in Elementor.
        $existing_raw = get_post_meta($page_id, '_elementor_data', true);
        $existing_data = null;
        if (is_string($existing_raw) && !empty($existing_raw)) {
            $decoded = json_decode($existing_raw, true);
            if (is_array($decoded)) {
                $existing_data = $decoded;
            }
        }

        $elementor_data = null;
        $used_existing_layout = false;
        $updated_widgets = 0;
        $found_text_widgets = 0;
        $appended_widget = false;
        $mapping_debug = array();
        $override_applied = false;
        if ($preserve_layout) {
            if (!is_array($existing_data) || empty($existing_data)) {
                return new WP_Error(
                    'missing_existing_layout',
                    'Preserve layout is enabled but existing Elementor layout was not found.',
                    array('status' => 409)
                );
            }

            if (is_array($elementor_data_override) && !empty($elementor_data_override)) {
                $elementor_data = $elementor_data_override;
                $used_existing_layout = true;
                $override_applied = true;
                $updated_widgets = 1;
                $mapping_debug['override_mode'] = true;
                $mapping_debug['override_nodes'] = is_array($elementor_data_override) ? count($elementor_data_override) : 0;
            } else {
                $sections = $this->split_content_sections($content_html);
                $structured_sections = $this->parse_structured_sections($content_html);
                $labeled_map = $this->parse_labeled_sections_map($content_html);
                $mapping_debug['parsed_sections'] = array();
                foreach ($structured_sections as $ps) {
                    $mapping_debug['parsed_sections'][] = array(
                        'title' => isset($ps['title']) ? $ps['title'] : '',
                        'values' => isset($ps['values']) && is_array($ps['values']) ? count($ps['values']) : 0,
                    );
                }
                $mapping_debug['labeled_map_sections'] = array_keys($labeled_map);
                $section_index = 0;
                if (is_array($existing_data) && !empty($existing_data)) {
                    $labeled_applied = false;
                    $required_sections = array('hero', 'about', 'services', 'team', 'projects', 'testimonials', 'blog', 'cta');
                    $missing_required = array();
                    foreach ($required_sections as $rk) {
                        if (!isset($labeled_map[$rk]) || !is_array($labeled_map[$rk]) || empty($labeled_map[$rk])) {
                            $missing_required[] = $rk;
                        }
                    }
                    $mapping_debug['strict_labeled_mapping'] = $strict_labeled_mapping;
                    $mapping_debug['missing_required_sections'] = $missing_required;
                    if (!empty($labeled_map) && count($labeled_map) >= 3) {
                        $before = $updated_widgets;
                        $this->apply_home03_labeled_mapping(
                            $existing_data,
                            $labeled_map,
                            $found_text_widgets,
                            $updated_widgets,
                            $mapping_debug
                        );
                        $labeled_applied = ($updated_widgets > $before);
                        $mapping_debug['labeled_applied'] = $labeled_applied;
                    }
                    if ($strict_labeled_mapping) {
                        if (!empty($missing_required)) {
                            return new WP_Error(
                                'strict_mapping_missing_sections',
                                'Strict mapping failed: missing required labeled sections: ' . implode(', ', $missing_required),
                                array('status' => 409, 'mapping_debug' => $mapping_debug)
                            );
                        }
                        if (!$labeled_applied) {
                            return new WP_Error(
                                'strict_mapping_no_updates',
                                'Strict mapping failed: no deterministic labeled updates were applied.',
                                array('status' => 409, 'mapping_debug' => $mapping_debug)
                            );
                        }
                    }
                    // Prefer explicit section mapping when content is structured (1,2,3...).
                    $use_structured = !empty($structured_sections) && count($structured_sections) >= 6 && !$labeled_applied && !$strict_labeled_mapping;
                    if ($use_structured) {
                        $structured_map = $this->build_structured_value_map($structured_sections);
                        $mapping_debug['structured_keys'] = array_keys($structured_map);
                        foreach ($existing_data as $sec_index => &$section_block) {
                            if (!is_array($section_block) || !isset($section_block['elements']) || !is_array($section_block['elements'])) {
                                continue;
                            }

                            $widget_counts = array();
                            $sample_texts = array();
                            $this->collect_section_summary($section_block['elements'], $widget_counts, $sample_texts);
                            $section_key = $this->detect_section_key_from_widgets($widget_counts, $sec_index);
                            $mapping_debug['sections'][] = array(
                                'index' => $sec_index,
                                'detected_key' => $section_key,
                                'widgets' => array_keys($widget_counts),
                            );
                            if ($section_key === '' || !isset($structured_map[$section_key])) {
                                continue;
                            }
                            // Top bar usually belongs to theme header and is not part of Elementor body.
                            if ($section_key === 'top_bar') {
                                continue;
                            }
                            $section_values = $structured_map[$section_key];
                            if ($section_key === 'testimonials' && isset($structured_map['stats']) && !empty($structured_map['stats'])) {
                                $section_values = array_merge($section_values, $structured_map['stats']);
                            }
                            if (empty($section_values)) {
                                continue;
                            }
                            $local_index = 0;
                            $before_updated = $updated_widgets;
                            $this->apply_structured_mapping_to_elements(
                                $section_block['elements'],
                                $section_key,
                                $section_values,
                                $local_index,
                                $found_text_widgets,
                                $updated_widgets
                            );
                            $mapping_debug['sections'][count($mapping_debug['sections']) - 1]['input_values'] = count($section_values);
                            $mapping_debug['sections'][count($mapping_debug['sections']) - 1]['updated_delta'] = $updated_widgets - $before_updated;
                        }
                        unset($section_block);
                    } else {
                        // Fallback: sequential mapping across full page.
                        $flat_values = $this->flatten_structured_values(array(array('values' => $sections)));
                        $section_index = 0;
                        foreach ($existing_data as $sec_index => &$section_block) {
                            // Skip heading-like replacements in first section in fallback mode.
                            $allow_heading_like = ($sec_index > 0);
                            if (is_array($section_block) && isset($section_block['elements']) && is_array($section_block['elements'])) {
                                $this->update_rich_text_widgets_sequential(
                                    $section_block['elements'],
                                    $flat_values,
                                    $section_index,
                                    $found_text_widgets,
                                    $updated_widgets,
                                    $allow_heading_like
                                );
                            }
                        }
                        unset($section_block);
                    }
                }
                if ($found_text_widgets <= 0) {
                    if ($replace_existing_text_only) {
                        return new WP_Error(
                            'no_replace_targets',
                            'No text-capable sections found in selected page to replace while preserving layout.',
                            array('status' => 409)
                        );
                    }
                    // Optional fallback mode (disabled by default): append new content widget.
                    $this->append_text_editor_to_first_column($existing_data, $content_html, $appended_widget);
                    if (!$appended_widget) {
                        return new WP_Error(
                            'no_replace_targets',
                            'No text-capable sections found in selected page and could not append content widget while preserving layout.',
                            array('status' => 409)
                        );
                    }
                }

                $elementor_data = $existing_data;
                $used_existing_layout = true;
            }
        }

        if (!is_array($elementor_data)) {
            $fallback_title = !empty($title) ? $title : get_the_title($page_id);
            $elementor_data = $this->build_basic_elementor_data($fallback_title, $content_html);
        }

        update_post_meta($page_id, '_elementor_edit_mode', 'builder');
        update_post_meta($page_id, '_elementor_template_type', 'wp-page');
        if (defined('ELEMENTOR_VERSION')) {
            update_post_meta($page_id, '_elementor_version', ELEMENTOR_VERSION);
        }
        update_post_meta($page_id, '_elementor_data', wp_slash(wp_json_encode($elementor_data)));

        // Clear Elementor cache so frontend shows updated content immediately.
        if (did_action('elementor/loaded') && class_exists('\Elementor\Plugin')) {
            \Elementor\Plugin::instance()->files_manager->clear_cache();
        }

        return array(
            'status' => 'success',
            'message' => 'Page updated successfully',
            'id' => $page_id,
            'link' => get_permalink($page_id),
            'edit_url' => admin_url('post.php?post=' . $page_id . '&action=edit'),
            'used_existing_layout' => $used_existing_layout,
            'updated_text_widgets' => $updated_widgets,
            'found_text_widgets' => $found_text_widgets,
            'appended_content_widget' => $appended_widget,
            'override_applied' => $override_applied,
            'plugin_version' => '1.1.21',
            'mapping_debug' => $mapping_debug,
        );
    }
    
    public function register_with_portal($request) {
        $data = $request->get_json_params();
        
        // Store registration data
        if (isset($data['portal_url'])) {
            update_option('revpublish_portal_url', $data['portal_url']);
        }
        
        if (isset($data['site_secret'])) {
            update_option('revpublish_site_secret', $data['site_secret']);
        }
        
        if (isset($data['site_id'])) {
            update_option('revpublish_site_id', $data['site_id']);
        }
        
        update_option('revpublish_registered_at', current_time('mysql'));
        
        return array(
            'status' => 'success',
            'message' => 'Site registered successfully',
            'site_info' => $this->get_site_info($request),
        );
    }
    
    public function add_admin_menu() {
        add_options_page(
            'RevPublish Settings',
            'RevPublish',
            'manage_options',
            'revpublish-connector',
            array($this, 'admin_page')
        );
    }
    
    public function admin_page() {
        $portal_url = get_option('revpublish_portal_url', '');
        $site_secret = get_option('revpublish_site_secret', '');
        $site_id = get_option('revpublish_site_id', '');
        
        if (isset($_POST['revpublish_save'])) {
            check_admin_referer('revpublish_settings');
            
            update_option('revpublish_portal_url', sanitize_text_field($_POST['portal_url']));
            
            if (empty($site_secret)) {
                $new_secret = wp_generate_password(32, false);
                update_option('revpublish_site_secret', $new_secret);
                $site_secret = $new_secret;
            }
            
            echo '<div class="notice notice-success"><p>Settings saved!</p></div>';
        }
        
        ?>
        <div class="wrap">
            <h1>RevPublish Connector Settings</h1>
            <form method="post" action="">
                <?php wp_nonce_field('revpublish_settings'); ?>
                <table class="form-table">
                    <tr>
                        <th><label for="portal_url">RevPublish Portal URL</label></th>
                        <td>
                            <input type="url" id="portal_url" name="portal_url" 
                                   value="<?php echo esc_attr($portal_url); ?>" 
                                   class="regular-text" 
                                   placeholder="https://your-portal.com" />
                            <p class="description">Your RevPublish portal URL</p>
                        </td>
                    </tr>
                    <tr>
                        <th><label>Site ID</label></th>
                        <td>
                            <code><?php echo esc_html($site_id ?: 'Not set'); ?></code>
                            <p class="description">Unique identifier for this site</p>
                        </td>
                    </tr>
                    <tr>
                        <th><label>Site Secret</label></th>
                        <td>
                            <code><?php echo esc_html($site_secret ?: 'Not set'); ?></code>
                            <p class="description">Secret key for API authentication</p>
                        </td>
                    </tr>
                    <tr>
                        <th><label>API Endpoint</label></th>
                        <td>
                            <code><?php echo esc_url(rest_url('revpublish/v1/site-info')); ?></code>
                            <p class="description">Use this URL to connect from RevPublish portal</p>
                        </td>
                    </tr>
                </table>
                <?php submit_button('Save Settings', 'primary', 'revpublish_save'); ?>
            </form>
            
            <h2>How to Connect</h2>
            <ol>
                <li>Copy the <strong>API Endpoint</strong> URL above</li>
                <li>Copy the <strong>Site Secret</strong> above</li>
                <li>In RevPublish portal, add this site using the endpoint and secret</li>
                <li>The portal will automatically discover and register this site</li>
            </ol>
        </div>
        <?php
    }
    
    public function activate() {
        // Generate site ID and secret on first activation
        if (empty(get_option('revpublish_site_id'))) {
            update_option('revpublish_site_id', wp_generate_uuid4());
        }
        
        if (empty(get_option('revpublish_site_secret'))) {
            update_option('revpublish_site_secret', wp_generate_password(32, false));
        }
        
        // Flush rewrite rules
        flush_rewrite_rules();
    }
}

// Initialize plugin
new RevPublishConnector();

