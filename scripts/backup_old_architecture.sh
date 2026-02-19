#!/bin/bash
# Backup OLD architecture before removal
# Part of architecture-cleanup spec Task 3.1

set -e  # Exit on error

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_BASE_DIR="${HOME}/gpubroker-apps-backup"
BACKUP_DIR="${BACKUP_BASE_DIR}/backup_${TIMESTAMP}"
SOURCE_DIR="backend/gpubroker/apps"
BACKUP_LOG="${BACKUP_DIR}/backup_manifest.txt"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== GPUBROKER OLD Architecture Backup ===${NC}"
echo "Timestamp: ${TIMESTAMP}"
echo "Source: ${SOURCE_DIR}"
echo "Destination: ${BACKUP_DIR}"
echo ""

# Verify source directory exists
if [ ! -d "${SOURCE_DIR}" ]; then
    echo -e "${RED}ERROR: Source directory ${SOURCE_DIR} does not exist!${NC}"
    exit 1
fi

# Create backup directory
echo -e "${YELLOW}Creating backup directory...${NC}"
mkdir -p "${BACKUP_DIR}"

# Copy the entire apps directory
echo -e "${YELLOW}Copying OLD architecture...${NC}"
cp -r "${SOURCE_DIR}" "${BACKUP_DIR}/"

# Create manifest file
echo -e "${YELLOW}Creating backup manifest...${NC}"
cat > "${BACKUP_LOG}" <<EOF
GPUBROKER OLD Architecture Backup
==================================
Backup Date: $(date)
Backup Timestamp: ${TIMESTAMP}
Source Directory: ${SOURCE_DIR}
Backup Location: ${BACKUP_DIR}
Hostname: $(hostname)
User: $(whoami)

Purpose:
--------
This backup was created as part of the architecture-cleanup spec (Task 3.1)
before removing the OLD architecture located at backend/gpubroker/apps/.

The OLD architecture is being removed because:
1. It duplicates functionality in backend/gpubroker/gpubrokerpod/gpubrokerapp/apps/
2. Django settings point to the POD architecture (INSTALLED_APPS)
3. Keeping both creates confusion and maintenance burden

Recovery Instructions:
----------------------
To restore this backup if needed:
1. Navigate to project root
2. Remove current apps directory: rm -rf backend/gpubroker/apps
3. Restore backup: cp -r ${BACKUP_DIR}/apps backend/gpubroker/
4. Update Django settings if needed

Directory Structure:
--------------------
EOF

# Add directory tree to manifest
echo "" >> "${BACKUP_LOG}"
if command -v tree &> /dev/null; then
    tree "${BACKUP_DIR}/apps" >> "${BACKUP_LOG}" 2>&1 || true
else
    find "${BACKUP_DIR}/apps" -type f >> "${BACKUP_LOG}" 2>&1 || true
fi

# Count files and calculate size
FILE_COUNT=$(find "${BACKUP_DIR}/apps" -type f | wc -l)
BACKUP_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)

echo "" >> "${BACKUP_LOG}"
echo "Backup Statistics:" >> "${BACKUP_LOG}"
echo "------------------" >> "${BACKUP_LOG}"
echo "Total Files: ${FILE_COUNT}" >> "${BACKUP_LOG}"
echo "Total Size: ${BACKUP_SIZE}" >> "${BACKUP_LOG}"

# Verify backup integrity
echo -e "${YELLOW}Verifying backup integrity...${NC}"
VERIFICATION_FAILED=0

# Check if key directories exist in backup
for dir in "ai_assistant" "auth_app" "kpi" "providers" "security"; do
    if [ ! -d "${BACKUP_DIR}/apps/${dir}" ]; then
        echo -e "${RED}ERROR: Directory ${dir} missing from backup!${NC}"
        VERIFICATION_FAILED=1
    fi
done

# Check if key files exist
for file in "__init__.py"; do
    if [ ! -f "${BACKUP_DIR}/apps/${file}" ]; then
        echo -e "${RED}ERROR: File ${file} missing from backup!${NC}"
        VERIFICATION_FAILED=1
    fi
done

if [ ${VERIFICATION_FAILED} -eq 1 ]; then
    echo -e "${RED}Backup verification FAILED!${NC}"
    exit 1
fi

# Create a symlink to latest backup
ln -sfn "${BACKUP_DIR}" "${BACKUP_BASE_DIR}/latest"

# Create recovery instructions file
cat > "${BACKUP_BASE_DIR}/RECOVERY_INSTRUCTIONS.md" <<EOF
# GPUBROKER OLD Architecture Recovery Instructions

## Latest Backup
- **Location**: \`${BACKUP_DIR}\`
- **Date**: $(date)
- **Symlink**: \`${BACKUP_BASE_DIR}/latest\` points to latest backup

## Quick Recovery

### Full Restoration
\`\`\`bash
# Navigate to project root
cd /path/to/gpubroker

# Remove current apps directory (if exists)
rm -rf backend/gpubroker/apps

# Restore from latest backup
cp -r ${BACKUP_BASE_DIR}/latest/apps backend/gpubroker/

# Verify restoration
ls -la backend/gpubroker/apps/
\`\`\`

### Partial Restoration (Single App)
\`\`\`bash
# Example: Restore only auth_app
cp -r ${BACKUP_BASE_DIR}/latest/apps/auth_app backend/gpubroker/apps/
\`\`\`

## Backup Manifest
See \`${BACKUP_DIR}/backup_manifest.txt\` for complete backup details.

## All Backups
\`\`\`bash
ls -lh ${BACKUP_BASE_DIR}/
\`\`\`

## Verification
\`\`\`bash
# Check backup integrity
diff -r backend/gpubroker/apps ${BACKUP_BASE_DIR}/latest/apps
\`\`\`
EOF

# Success summary
echo ""
echo -e "${GREEN}=== Backup Completed Successfully ===${NC}"
echo -e "${GREEN}✓${NC} Backup Location: ${BACKUP_DIR}"
echo -e "${GREEN}✓${NC} Latest Symlink: ${BACKUP_BASE_DIR}/latest"
echo -e "${GREEN}✓${NC} Files Backed Up: ${FILE_COUNT}"
echo -e "${GREEN}✓${NC} Total Size: ${BACKUP_SIZE}"
echo -e "${GREEN}✓${NC} Manifest: ${BACKUP_LOG}"
echo -e "${GREEN}✓${NC} Recovery Instructions: ${BACKUP_BASE_DIR}/RECOVERY_INSTRUCTIONS.md"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review backup manifest: cat ${BACKUP_LOG}"
echo "2. Verify backup contents: ls -la ${BACKUP_DIR}/apps/"
echo "3. Proceed with architecture cleanup tasks"
echo ""
