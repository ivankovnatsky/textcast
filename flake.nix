{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/ef3f103a7a8a05e03bc6c1131d36a2f085c73942";
    flake-utils.url = "github:numtide/flake-utils/11707dc2f618dd54ca8739b309ec4fc024de578b";
  };
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem
      (system:
        let
          pkgs = import nixpkgs
            {
              inherit system;
              overlays = [
                (final: prev: { })
              ];
            };

          # Create a custom browsers-mac derivation that only installs Chromium
          playwright-browsers-chromium = pkgs.stdenv.mkDerivation {
            pname = "playwright-browsers-chromium";
            version = pkgs.playwright-test.version;

            dontUnpack = true;
            nativeBuildInputs = [ pkgs.cacert ];

            installPhase = ''
              export PLAYWRIGHT_BROWSERS_PATH=$out
              ${pkgs.playwright-test}/bin/playwright install chromium
              rm -r $out/.links
            '';
          };
        in
        with pkgs;
        {
          devShells.default = mkShell {
            buildInputs = [
              ffmpeg
              (python312.withPackages (ps: with ps; [
                # Code Deps
                beautifulsoup4
                elevenlabs
                click
                openai
                playwright
                pydub
                pytest
                readability-lxml
                requests
                requests-mock

                # Code Quality
                autoflake
              ]))
              playwright-test
            ];
            shellHook = ''
              export PLAYWRIGHT_BROWSERS_PATH="${playwright-browsers-chromium}"

              export OPENAI_API_KEY=$(ks show openai-api-key)
              export ELEVEN_API_KEY=$(ks show eleven-api-key)
            '';
          };
        }
      );
}
