#!/bin/bash
# ============================================================================
# GURU UNIFIED KNOWLEDGE LAYER - DEPLOYMENT SCRIPT
# Version: 1.0
# Date: December 28, 2025
# ============================================================================
#
# This script deploys the complete Unified Knowledge Layer system:
# 1. Database schema migration
# 2. Rule categorization
# 3. Prompt library seeding
# 4. API route updates
# 5. Service restart
#
# Usage:
#   ./deploy_unified_knowledge_layer.sh [--dry-run]
#
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VPS_HOST="217.15.168.106"
VPS_USER="root"
GURU_PATH="/opt/guru-intelligence"
DB_CONTAINER="knowledge-postgres"
DB_NAME="knowledge_graph_db"
DB_USER="knowledge_admin"

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}🔍 DRY RUN MODE - No changes will be made${NC}\n"
fi

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

run_sql() {
    local sql_file=$1
    local description=$2
    
    log_step "$description"
    
    if [ "$DRY_RUN" = true ]; then
        echo "   [DRY RUN] Would execute: $sql_file"
        return 0
    fi
    
    docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME < "$sql_file"
    
    if [ $? -eq 0 ]; then
        log_success "SQL executed successfully"
    else
        log_error "SQL execution failed"
        exit 1
    fi
}

run_python() {
    local script=$1
    local description=$2
    
    log_step "$description"
    
    if [ "$DRY_RUN" = true ]; then
        echo "   [DRY RUN] Would execute: $script"
        return 0
    fi
    
    cd $GURU_PATH
    source venv/bin/activate
    python3 "$script"
    
    if [ $? -eq 0 ]; then
        log_success "Python script completed successfully"
    else
        log_error "Python script failed"
        exit 1
    fi
}

# ============================================================================
# PRE-DEPLOYMENT CHECKS
# ============================================================================

echo "============================================================================"
echo "GURU UNIFIED KNOWLEDGE LAYER - DEPLOYMENT"
echo "============================================================================"
echo ""

log_step "Running pre-deployment checks..."

# Check if we're on the VPS
if [ "$(hostname -I | grep -o '217.15.168.106')" != "217.15.168.106" ]; then
    log_error "This script must be run on the VPS (217.15.168.106)"
    echo "Current IP: $(hostname -I)"
    exit 1
fi

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    log_error "Docker is not running or not accessible"
    exit 1
fi

# Check if database container exists
if ! docker ps | grep -q $DB_CONTAINER; then
    log_error "Database container '$DB_CONTAINER' is not running"
    exit 1
fi

# Check if Guru Intelligence directory exists
if [ ! -d "$GURU_PATH" ]; then
    log_error "Guru Intelligence directory not found: $GURU_PATH"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$GURU_PATH/venv" ]; then
    log_error "Python virtual environment not found: $GURU_PATH/venv"
    exit 1
fi

log_success "All pre-deployment checks passed"
echo ""

# ============================================================================
# BACKUP CURRENT STATE
# ============================================================================

log_step "Creating backup of current database state..."

if [ "$DRY_RUN" = false ]; then
    BACKUP_FILE="guru_backup_$(date +%Y%m%d_%H%M%S).sql"
    docker exec $DB_CONTAINER pg_dump -U $DB_USER $DB_NAME > "$GURU_PATH/backups/$BACKUP_FILE"
    log_success "Backup created: $BACKUP_FILE"
else
    echo "   [DRY RUN] Would create backup"
fi

echo ""

# ============================================================================
# PHASE 1: DATABASE SCHEMA MIGRATION
# ============================================================================

echo "============================================================================"
echo "PHASE 1: DATABASE SCHEMA MIGRATION"
echo "============================================================================"
echo ""

# Copy SQL file to VPS if running locally
# (Assuming files are already on VPS for this script)

run_sql "$GURU_PATH/migrations/guru-unified-schema-migration.sql" \
        "Applying schema migration (new tables + columns)"

# Verify schema changes
log_step "Verifying schema changes..."
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "\dt" | grep -E "(knowledge_items|prompt_templates|scoring_frameworks)"
log_success "Schema verification complete"

echo ""

# ============================================================================
# PHASE 2: RULE CATEGORIZATION
# ============================================================================

echo "============================================================================"
echo "PHASE 2: RULE CATEGORIZATION"
echo "============================================================================"
echo ""

run_python "$GURU_PATH/scripts/categorize_rules.py" \
           "Categorizing 359 rules by complexity level (Tier 1/2/3)"

# Display categorization summary
log_step "Categorization summary:"
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
SELECT complexity_level, COUNT(*) as count, 
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage
FROM extracted_rules
WHERE is_active = TRUE
GROUP BY complexity_level
ORDER BY complexity_level;"

echo ""

# ============================================================================
# PHASE 3: PROMPT LIBRARY SEEDING
# ============================================================================

echo "============================================================================"
echo "PHASE 3: PROMPT LIBRARY SEEDING"
echo "============================================================================"
echo ""

run_sql "$GURU_PATH/migrations/seed_prompt_library.sql" \
        "Seeding prompt_templates with core prompts"

# Display prompt counts
log_step "Prompt library summary:"
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
SELECT prompt_type, COUNT(*) as count
FROM prompt_templates
WHERE is_active = TRUE
GROUP BY prompt_type
ORDER BY prompt_type;"

echo ""

# ============================================================================
# PHASE 4: INSTALL PYTHON DEPENDENCIES
# ============================================================================

echo "============================================================================"
echo "PHASE 4: PYTHON DEPENDENCIES"
echo "============================================================================"
echo ""

log_step "Installing required Python packages..."

if [ "$DRY_RUN" = false ]; then
    cd $GURU_PATH
    source venv/bin/activate
    
    pip install --upgrade pip
    pip install spacy textstat anthropic psycopg2-binary
    python -m spacy download en_core_web_sm
    
    log_success "Python dependencies installed"
else
    echo "   [DRY RUN] Would install: spacy, textstat, anthropic"
fi

echo ""

# ============================================================================
# PHASE 5: UPDATE API ROUTES
# ============================================================================

echo "============================================================================"
echo "PHASE 5: API ROUTES UPDATE"
echo "============================================================================"
echo ""

log_step "Backing up current API routes..."

if [ "$DRY_RUN" = false ]; then
    cp "$GURU_PATH/src/api/knowledge_routes.py" \
       "$GURU_PATH/src/api/knowledge_routes.py.backup.$(date +%Y%m%d_%H%M%S)"
    log_success "Backup created"
else
    echo "   [DRY RUN] Would backup knowledge_routes.py"
fi

log_step "Installing new unified API routes..."

if [ "$DRY_RUN" = false ]; then
    # Copy new files
    cp "$GURU_PATH/migrations/multi_tiered_assessor.py" "$GURU_PATH/src/"
    cp "$GURU_PATH/migrations/unified_knowledge_routes.py" "$GURU_PATH/src/api/"
    
    # Update main.py to include new routers
    log_step "Updating main.py to register new routers..."
    
    # This would need specific implementation based on current main.py structure
    # For now, provide manual instructions
    
    log_warning "MANUAL STEP REQUIRED:"
    echo "   Edit $GURU_PATH/src/main.py and add:"
    echo ""
    echo "   from api.unified_knowledge_routes import knowledge_router, prompts_router, scoring_router"
    echo ""
    echo "   app.include_router(knowledge_router)"
    echo "   app.include_router(prompts_router)"
    echo "   app.include_router(scoring_router)"
    echo ""
    
    read -p "Press Enter after updating main.py to continue..."
    
    log_success "API routes updated"
else
    echo "   [DRY RUN] Would copy new route files"
fi

echo ""

# ============================================================================
# PHASE 6: RESTART GURU SERVICE
# ============================================================================

echo "============================================================================"
echo "PHASE 6: SERVICE RESTART"
echo "============================================================================"
echo ""

log_step "Restarting Guru Intelligence service..."

if [ "$DRY_RUN" = false ]; then
    systemctl restart guru-intelligence
    sleep 3
    
    # Verify service is running
    if systemctl is-active --quiet guru-intelligence; then
        log_success "Guru Intelligence service restarted successfully"
    else
        log_error "Service failed to start - check logs: journalctl -u guru-intelligence -n 50"
        exit 1
    fi
else
    echo "   [DRY RUN] Would restart guru-intelligence service"
fi

echo ""

# ============================================================================
# PHASE 7: VERIFICATION TESTS
# ============================================================================

echo "============================================================================"
echo "PHASE 7: VERIFICATION TESTS"
echo "============================================================================"
echo ""

log_step "Running verification tests..."

if [ "$DRY_RUN" = false ]; then
    # Test 1: Health check
    log_step "Test 1: Health check"
    curl -s http://localhost:8103/health | grep -q "ok" && log_success "Health check passed"
    
    # Test 2: Stats endpoint
    log_step "Test 2: Stats endpoint"
    STATS_RESPONSE=$(curl -s http://localhost:8103/knowledge/stats)
    echo "$STATS_RESPONSE" | jq '.rules.total' > /dev/null && log_success "Stats endpoint working"
    
    # Test 3: Prompt library
    log_step "Test 3: Prompt library endpoint"
    curl -s http://localhost:8103/prompts/ | jq '.count' > /dev/null && log_success "Prompt library accessible"
    
    # Test 4: Multi-tiered assessment
    log_step "Test 4: Multi-tiered assessment"
    TEST_CONTENT="Phoenix plumbers charge \$150-\$450 for drain cleaning. ABC Plumbing (ROC-284756) serves Mesa, Tempe, Scottsdale. Call (602) 555-1234."
    
    ASSESS_RESPONSE=$(curl -s -X POST http://localhost:8103/knowledge/assess \
        -H "Content-Type: application/json" \
        -d "{\"content\": \"$TEST_CONTENT\", \"page_type\": \"service\"}")
    
    echo "$ASSESS_RESPONSE" | jq '.overall_score' > /dev/null && log_success "Multi-tiered assessment working"
    
    # Display assessment result
    echo ""
    echo "Sample Assessment Result:"
    echo "$ASSESS_RESPONSE" | jq '{score: .overall_score, passed: .passed, tiers_run: .tiers_run, cost: .api_cost}'
    
else
    echo "   [DRY RUN] Would run verification tests"
fi

echo ""

# ============================================================================
# DEPLOYMENT SUMMARY
# ============================================================================

echo "============================================================================"
echo "DEPLOYMENT SUMMARY"
echo "============================================================================"
echo ""

if [ "$DRY_RUN" = false ]; then
    log_success "Unified Knowledge Layer deployment COMPLETE!"
    
    echo ""
    echo "System Status:"
    docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
    SELECT 
        'Rules' as item, COUNT(*) as count 
    FROM extracted_rules WHERE is_active = TRUE
    UNION ALL
    SELECT 
        'Tier 1 Rules', COUNT(*) 
    FROM extracted_rules WHERE complexity_level = 1 AND is_active = TRUE
    UNION ALL
    SELECT 
        'Tier 2 Rules', COUNT(*) 
    FROM extracted_rules WHERE complexity_level = 2 AND is_active = TRUE
    UNION ALL
    SELECT 
        'Tier 3 Rules', COUNT(*) 
    FROM extracted_rules WHERE complexity_level = 3 AND is_active = TRUE
    UNION ALL
    SELECT 
        'Prompts', COUNT(*) 
    FROM prompt_templates WHERE is_active = TRUE;"
    
    echo ""
    echo "Available Endpoints:"
    echo "  POST   /knowledge/assess       - Multi-tiered content validation"
    echo "  POST   /knowledge/rules        - Query rules by filters"
    echo "  GET    /knowledge/stats        - System statistics"
    echo "  GET    /prompts/               - List prompts"
    echo "  GET    /prompts/{id}           - Get specific prompt"
    echo "  POST   /prompts/render         - Render prompt with variables"
    echo "  GET    /scoring/frameworks     - List scoring frameworks"
    echo "  POST   /scoring/score          - Apply framework to content"
    
    echo ""
    echo "Next Steps:"
    echo "  1. Test assessment API with R&R content samples"
    echo "  2. Add Tier 3 prompt templates for remaining rules"
    echo "  3. Create scoring frameworks (E-E-A-T, GEO, etc.)"
    echo "  4. Update guru_validator.py in R&R Automation to use new API"
    echo "  5. Monitor API costs and performance metrics"
    
    echo ""
    log_success "Deployment completed successfully at $(date)"
    
else
    echo ""
    log_warning "DRY RUN COMPLETE - No changes were made"
    echo ""
    echo "To deploy for real, run:"
    echo "  ./deploy_unified_knowledge_layer.sh"
fi

echo ""
echo "============================================================================"
