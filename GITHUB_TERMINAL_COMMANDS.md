# GitHub Terminal Commands

```bash
cd ~/Downloads

unzip -o SchoolMealAllergenSafetyMonitor_Local_All_Files.zip

cd SchoolMealAllergenSafetyMonitor_Local

git init
git branch -M main

git add -A
git diff --cached --name-only

git commit -m "feat: add AllergenSafe school meal safety monitor"

git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/shaunakmirajgaonkar/school-meal-allergen-safety-monitor.git

git push -u origin main
```

Verify:

```bash
git status
git ls-files
git remote -v
```
