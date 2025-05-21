#!/usr/bin/env bash

python -m articast \
	--directory /storage/Data/Drive/Articast/Audio \
	--file-url-list /storage/Data/Drive/Articast/Articles/Articles.txt \
	--condense \
	--condense-ratio 0.5 \
	--yes
