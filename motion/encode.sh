#!/bin/bash
# د Blender فریمونه په ویډیو بدلوي
IN=$1; OUT=$2; mkdir -p $OUT
GLOW="split[a][b];[b]gblur=sigma=18,eq=brightness=0.02[g];[a][g]blend=all_mode=screen:all_opacity=0.35,format=yuv420p"
for s in intro outro; do
  [ -d $IN/$s ] || continue
  ffmpeg -y -loglevel error -framerate 30 -i $IN/$s/${s}_%04d.png -vf "$GLOW" -c:v libx264 -preset slow -crf 17 -movflags +faststart $OUT/$s.mp4
done
for s in lt_in lt_out stinger; do
  [ -d $IN/$s ] || continue
  ffmpeg -y -loglevel error -framerate 30 -i $IN/$s/${s}_%04d.png -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 22 -auto-alt-ref 0 $OUT/$s.webm
done
[ -f $IN/lt_hold/lt_hold_0001.png ] && cp $IN/lt_hold/lt_hold_0001.png $OUT/lt_hold.png
ls -la $OUT
