<?php

if (!defined('WP_UNINSTALL_PLUGIN')) {
    exit;
}

global $wpdb;

// Remove all plugin transients.
$like = '_transient_pci_content_%';
$like_timeout = '_transient_timeout_pci_content_%';

$wpdb->query(
    $wpdb->prepare(
        "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s OR option_name LIKE %s",
        $like,
        $like_timeout
    )
);
