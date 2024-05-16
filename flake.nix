{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/062ca2a9370a27a35c524dc82d540e6e9824b652";
    flake-utils.url = "github:numtide/flake-utils/b1d9ab70662946ef0850d488da1c9019f3a9752a";
  };
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem
      (system:
        let
          pkgs = import nixpkgs {
            inherit system;
          };
        in
        with pkgs;
        {
          devShells.default = mkShell {
            buildInputs = [
              ffmpeg
              (python311.withPackages (ps: with ps; [
                beautifulsoup4
                click
                openai
                playwright
                pydub
                pytest
                readability-lxml
                requests
              ]))
            ];
            shellHook = ''
              export PLAYWRIGHT_BROWSERS_PATH="$PWD/playwright-browsers"
              if [[ ! -d "$PLAYWRIGHT_BROWSERS_PATH" ]]; then
                echo "Installing Playwright browsers in $PLAYWRIGHT_BROWSERS_PATH"
                playwright install chromium
              else
                echo "Playwright browsers already installed in $PLAYWRIGHT_BROWSERS_PATH"
              fi
              $SHELL
            '';
          };
        }
      );
}
