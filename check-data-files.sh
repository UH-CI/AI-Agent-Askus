#!/bin/bash

# Data Files Check Script for AI-Agent-Askus
# This script checks what data files are available for loading

echo "🔍 Checking available data files for AI-Agent-Askus..."
echo ""

# Check required data files
echo "📚 Required Data Files:"

if [ -d "app/data/askus" ]; then
    FAQ_COUNT=$(find app/data/askus -name "*.html" | wc -l)
    echo "✅ FAQ data: app/data/askus/ ($FAQ_COUNT HTML files)"
else
    echo "❌ FAQ data: app/data/askus/ (MISSING - REQUIRED)"
fi

if [ -f "app/data/json/policies.json" ]; then
    echo "✅ UH Policies: app/data/json/policies.json"
else
    echo "❌ UH Policies: app/data/json/policies.json (MISSING - REQUIRED)"
fi

echo ""
echo "🔧 Optional Data Files:"

# Check TeamDynamix data in multiple locations
TDX_FOUND=false
TDX_PATHS=(
    "web-scraper/data/kb_articles_extracted.json"
    "app/data/json/teamdynamix.json"
)

for path in "${TDX_PATHS[@]}"; do
    if [ -f "$path" ]; then
        echo "✅ TeamDynamix KB: $path"
        TDX_FOUND=true
    fi
done

if [ "$TDX_FOUND" = false ]; then
    echo "⚠️  TeamDynamix KB: Not found (optional)"
    echo "   Searched locations:"
    for path in "${TDX_PATHS[@]}"; do
        echo "   - $path"
    done
fi

echo ""
echo "📊 Data Summary:"

REQUIRED_OK=true
if [ ! -d "app/data/askus" ]; then
    REQUIRED_OK=false
fi
if [ ! -f "app/data/json/policies.json" ]; then
    REQUIRED_OK=false
fi

if [ "$REQUIRED_OK" = true ]; then
    echo "✅ All required data files are present"
    if [ "$TDX_FOUND" = true ]; then
        echo "✅ Optional TeamDynamix data is also available"
        echo "🎉 Complete dataset ready for loading!"
    else
        echo "⚠️  Optional TeamDynamix data is missing (deployment will still work)"
        echo "✅ Core dataset ready for loading!"
    fi
else
    echo "❌ Some required data files are missing"
    echo "   The application may not function properly without these files"
fi

echo ""
echo "💡 To generate missing TeamDynamix data:"
echo "   cd web-scraper"
echo "   python extract_kb_articles.py"
