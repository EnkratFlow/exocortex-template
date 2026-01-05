# Exocortex Template Initialization Script (PowerShell)
# Replaces placeholders with your project-specific values

param()

Write-Host ""
Write-Host "🧠 Exocortex Template Initialization" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Check if directories exist first (fail fast)
if (-not (Test-Path ".exocortex")) {
    Write-Host "❌ Error: .exocortex directory not found in current directory" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run this script from your project root after copying:" -ForegroundColor Yellow
    Write-Host "  - .exocortex/" -ForegroundColor Yellow
    Write-Host "  - docs\control\" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Example:" -ForegroundColor Yellow
    Write-Host "  cd C:\path\to\your-project" -ForegroundColor Yellow
    Write-Host "  .\init-project.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

if (-not (Test-Path "docs\control")) {
    Write-Host "❌ Error: docs\control directory not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please ensure you've copied both:" -ForegroundColor Yellow
    Write-Host "  - .exocortex\" -ForegroundColor Yellow
    Write-Host "  - docs\control\" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "✓ Found .exocortex\ and docs\control\ directories" -ForegroundColor Green
Write-Host ""

# Prompt for project name
$projectName = Read-Host "📝 Enter your project name (e.g., my-awesome-app)"
if ([string]::IsNullOrWhiteSpace($projectName)) {
    Write-Host "❌ Error: Project name cannot be empty" -ForegroundColor Red
    exit 1
}

# Prompt for parent project (optional)
$parentProject = Read-Host "📝 Enter parent project name (optional, press Enter to skip)"
if ([string]::IsNullOrWhiteSpace($parentProject)) {
    $parentProject = "None"
}

# Get current date
$currentDate = Get-Date -Format "yyyy-MM-dd"

# Show summary
Write-Host ""
Write-Host "📋 Summary:" -ForegroundColor Yellow
Write-Host "  Project Name:    $projectName"
Write-Host "  Parent Project:  $parentProject"
Write-Host "  Date:            $currentDate"
Write-Host ""

# Confirm
$confirmation = Read-Host "✅ Continue with initialization? (y/n)"
if ($confirmation -notmatch '^[Yy]$') {
    Write-Host "❌ Initialization cancelled" -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "🔄 Replacing placeholders..." -ForegroundColor Cyan

# Find all .md files in .exocortex/ and docs/control/
$files = @(
    Get-ChildItem -Path ".exocortex" -Filter "*.md" -File -ErrorAction SilentlyContinue
    Get-ChildItem -Path "docs\control" -Filter "*.md" -File -ErrorAction SilentlyContinue
)

$fileCount = 0

# Escape special regex characters in replacement strings
$projectNameEscaped = [regex]::Escape($projectName)
$parentProjectEscaped = [regex]::Escape($parentProject)

foreach ($file in $files) {
    if ($file -ne $null) {
        try {
            # Read file content
            $content = Get-Content $file.FullName -Raw -ErrorAction Stop
            
            # Replace placeholders (using escaped strings for safety)
            $content = $content -replace '\[PROJECT_NAME\]', $projectName
            $content = $content -replace '\[PARENT_PROJECT\]', $parentProject
            $content = $content -replace '\[DATE\]', $currentDate
            
            # Write back to file
            Set-Content -Path $file.FullName -Value $content -NoNewline -ErrorAction Stop
            
            $fileCount++
            Write-Host "  ✓ Updated $($file.Name)" -ForegroundColor Green
        }
        catch {
            Write-Host "  ⚠ Warning: Could not update $($file.Name): $_" -ForegroundColor Yellow
        }
    }
}

if ($fileCount -eq 0) {
    Write-Host ""
    Write-Host "⚠️  Warning: No .md files found to process" -ForegroundColor Yellow
    Write-Host "   Make sure .exocortex/ and docs\control\ directories contain .md files" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "✅ Initialization Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Files updated: $fileCount"
Write-Host ""
Write-Host "🎯 Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Customize .exocortex\PROJECT_MEMORY.md (describe your system)"
Write-Host "  2. Customize .exocortex\ESSENTIAL_FILES.md (map your file locations)"
Write-Host "  3. Add your first tasks to .exocortex\TODO.md"
Write-Host "  4. Start working with '/work' command"
Write-Host ""
Write-Host "📖 Read .exocortex\README.md for complete usage guide"
Write-Host ""
Write-Host "🚀 Happy coding!" -ForegroundColor Cyan
Write-Host ""
