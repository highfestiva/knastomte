#!/bin/bash

cxfreeze knastomte.py --target-dir knastomte_win64
cp allocation.cfg knastomte_win64/
cd knastomte_win64/
mkdir input
/c/Program/7-Zip/7z.exe a knastomte *
mv knastomte.7z ..
cd ..
rm -Rf knastomte_win64
echo 'Done! Resulting 7z in current dir if all is well.'
