# Render with: vhs demo/demo.tape   (https://github.com/charmbracelet/vhs)
Output demo/demo.gif

Set Shell "bash"
Set FontSize 20
Set Width 1240
Set Height 680
Set Padding 22
Set Theme "Catppuccin Mocha"
Set WindowBar Colorful
Set TypingSpeed 45ms

Hide
Type `export PATH="$PWD/.venv/bin:$PATH" && rm -f demo.db mess_manifest.json && clear` Enter
Sleep 1s
Show

Type "# seed a messy 'enterprise' database in one command -- SQLite, no Docker"
Enter
Sleep 900ms
Type "DATABASE_URL=sqlite:///demo.db PARTS_COUNT=400 CHANGE_ORDERS_COUNT=1500 PURCHASE_ORDERS_COUNT=2000 AUDIT_LOG_COUNT=3000 python -m app.seed.run"
Enter
Sleep 7s
Type "# every injected defect is counted in the ground-truth manifest:"
Enter
Sleep 800ms
Type "python -m json.tool mess_manifest.json | head -22"
Enter
Sleep 3s
