@echo off
FOR /F "tokens=1-4 delims=/ " %%I IN ('DATE /t') DO SET thedate=%%L%%K%%J
set app_name=scummimg

cd src
E:\Apps\Programming\Python2.5\python.exe setup.py py2exe %1 --bundle 2
rd build /S /Q
rename dist %app_name%
mkdir ..\zip
move %app_name% ..\zip
cd ..\zip
mkdir %app_name%\docs
copy ..\docs\*.txt %app_name%\docs

E:\Utils\Misc\7-Zip\7z.exe a -tzip -mx9 -r -x!_bak -x!src ..\%app_name%_bin_%thedate%.zip %app_name%
cd ..
rd zip /s /q

mkdir zip
mkdir zip\%app_name%
mkdir zip\%app_name%\src
mkdir zip\%app_name%\docs
xcopy src zip\%app_name%\src /E /EXCLUDE:setup_src_exclusions.txt
copy *.bat zip\%app_name%\
copy setup_src_exclusions.txt zip\%app_name%\
xcopy docs\*.txt zip\%app_name%\docs

cd zip
E:\Utils\Misc\7-Zip\7z.exe a -tzip -mx9 -r -x!_bak -x!.\src ..\%app_name%_src_%thedate%.zip %app_name%
cd ..
rd zip /s /q