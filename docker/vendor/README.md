whisper-source.tar is generated from the installed upstream ggml-org/whisper.cpp
checkout, commit 727d3e7666485e12450746b523bfb4e7f057cc5e. It includes its MIT license.
Regenerate using: git -C .local-tools/whisper.cpp archive HEAD -o "$PWD/docker/vendor/whisper-source.tar"
