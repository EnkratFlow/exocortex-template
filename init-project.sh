#!/bin/bash

# Exocortex Template Initialization Script
# Replaces placeholders with your project-specific values
#
# USAGE: Run this script from your PROJECT ROOT directory after copying
#        the .exocortex/ and docs/control/ directories to your project.

echo ""
echo "🧠 Exocortex Template Initialization"
echo "===================================="
echo ""

# Check if .exocortex directory exists
if [ ! -d ".exocortex" ]; then
    echo "❌ Error: .exocortex directory not found in current directory"
    echo ""
    echo "Please run this script from your project root after copying:"
    echo "  - .exocortex/"
    echo "  - docs/control/"
    echo ""
    echo "Example:"
    echo "  cd /path/to/your-project"
    echo "  bash init-project.sh"
    echo ""
    exit 1
fi

# Check if docs/control directory exists
if [ ! -d "docs/control" ]; then
    echo "❌ Error: docs/control directory not found"
    echo ""
    echo "Please ensure you've copied both:"
    echo "  - .exocortex/"
    echo "  - docs/control/"
    echo ""
    exit 1
fi

echo "✓ Found .exocortex/ and docs/control/ directories"
echo ""

# Prompt for project name
read -p "📝 Enter your project name (e.g., my-awesome-app): " PROJECT_NAME
if [ -z "$PROJECT_NAME" ]; then
    echo "❌ Error: Project name cannot be empty"
    exit 1
fi

# Prompt for parent project (optional)
read -p "📝 Enter parent project name (optional, press Enter to skip): " PARENT_PROJECT
if [ -z "$PARENT_PROJECT" ]; then
    PARENT_PROJECT="None"
fi

# Get current date
CURRENT_DATE=$(date +%Y-%m-%d)

# Show summary
echo ""
echo "📋 Summary:"
echo "  Project Name:    $PROJECT_NAME"
echo "  Parent Project:  $PARENT_PROJECT"
echo "  Date:            $CURRENT_DATE"
echo ""

# Confirm
read -p "✅ Continue with initialization? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Initialization cancelled"
    exit 0
fi

echo ""
echo "🔄 Replacing placeholders..."

# Detect OS for sed compatibility
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    SED_INPLACE="sed -i .bak"
else
    # Linux
    SED_INPLACE="sed -i.bak"
fi

# Find all .md files in .exocortex/ and docs/control/
# Replace placeholders in each file
FILE_COUNT=0

for file in .exocortex/*.md docs/control/*.md; do
    if [ -f "$file" ]; then
        $SED_INPLACE "s/\[PROJECT_NAME\]/$PROJECT_NAME/g" "$file"
        $SED_INPLACE "s/\[PARENT_PROJECT\]/$PARENT_PROJECT/g" "$file"
        $SED_INPLACE "s/\[DATE\]/$CURRENT_DATE/g" "$file"
        ((FILE_COUNT++))
        echo "  ✓ Updated $file"
    fi
done

if [ "$FILE_COUNT" -eq 0 ]; then
    echo ""
    echo "⚠️  Warning: No .md files found to process"
    echo "   Make sure .exocortex/ and docs/control/ directories contain .md files"
    echo ""
    exit 1
fi

echo ""
echo "🧹 Cleaning up backup files..."

# Remove backup files created by sed
if ! find .exocortex/ docs/control/ -name "*.bak" -type f -delete 2>/dev/null; then
    echo "  ⚠️  Warning: Some backup files could not be deleted (check permissions)"
else
    echo "  ✓ Cleaned up backup files"
fi

echo ""
echo "✅ Initialization Complete!"
echo ""
echo "📁 Files updated: $FILE_COUNT"
echo ""
echo "🎯 Next Steps:"
echo "  1. Customize .exocortex/PROJECT_MEMORY.md (describe your system)"
echo "  2. Customize .exocortex/ESSENTIAL_FILES.md (map your file locations)"
echo "  3. Add your first tasks to .exocortex/TODO.md"
echo "  4. Start working with '/work' command"
echo ""
echo "📖 Read .exocortex/README.md for complete usage guide"
echo ""
echo "🚀 Happy coding!"
echo ""
