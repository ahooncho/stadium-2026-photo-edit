#!/bin/bash
# $1=id $2=title  -> 2000px thumb + first 64KB (EXIF)
S=${WORK:?set WORK=work dir}
n=${2%.JPG}
[ -s $S/thumbs/$n.jpg ] || curl -sfL --retry 4 -o $S/thumbs/$n.jpg "https://drive.google.com/thumbnail?id=$1&sz=w2000"
[ -s $S/exifhead/$n.bin ] || curl -sfL --retry 4 -r 0-98303 -o $S/exifhead/$n.bin "https://drive.usercontent.google.com/download?id=$1&export=download"
