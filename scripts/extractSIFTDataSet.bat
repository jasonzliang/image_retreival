::for %%a IN (%1\*.jpg) do convert %%a -resize 171x128 %1\%%~na.pgm
::"C:\earthMineData\app\jz\siftDemoV4\siftWin32.exe" <img\image0636.pgm >sift.txt


for %%a IN (%1\*.jpg) do convert %%a %1\%%~na.pgm
for %%b IN (%1\*.pgm) do "D:\Research\app\siftDemoV4\siftWin32.exe" <%%b >%1\%%~nbsift.txt

::