# iterate over files in this folder
for file in *.png; do
    # if the name of the file begins with icon
    if [[ $file == icon* ]]; then
        # get the name of the file without extension
        name="${file%.*}"
        convert ${file}  -background black -alpha background ${name}.jpg
    fi

done