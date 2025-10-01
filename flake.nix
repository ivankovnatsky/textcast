{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/6bd7ba77ef6015853d67a89bd59f01b2880e9050";
    flake-utils.url = "github:numtide/flake-utils/11707dc2f618dd54ca8739b309ec4fc024de578b";
  };
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [(final: prev: {})];
        };
        
        # Determine platform
        isLinux = pkgs.stdenv.hostPlatform.isLinux;
        isDarwin = pkgs.stdenv.hostPlatform.isDarwin;
        
        # Common Python packages for both platforms
        pythonPackages = ps: with ps; [
          # Core Dependencies
          beautifulsoup4
          click
          elevenlabs
          feedparser
          lxml
          openai
          playwright
          pydub
          pyyaml
          readability-lxml
          requests
          watchdog
          # Development & Testing
          pytest
          requests-mock
          cogapp
          # Code Quality
          autoflake
        ];
      in
      # Linux-specific configuration
      (if isLinux then {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            ffmpeg
            (python312.withPackages pythonPackages)
            playwright-test
            playwright-driver.browsers
            gh
            # Formatting tools
            treefmt
            nodePackages.prettier
            ruff
          ];
          
          shellHook = ''
            echo "Setting up Playwright for Linux environment..."
            export PLAYWRIGHT_BROWSERS_PATH=${pkgs.playwright-driver.browsers}
            
            export OPENAI_API_KEY=$(cat .secrets/openai-api-key)
            export ELEVEN_API_KEY=$(cat .secrets/eleven-api-key)
            export ABS_API_KEY=$(cat .secrets/abs-api-key)
            export ABS_URL=$(cat .secrets/abs-url)
          '';
        };
      }
      # macOS-specific configuration
      else {
        devShells.default = 
          let
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
          pkgs.mkShell {
            buildInputs = with pkgs; [
              ffmpeg
              (python312.withPackages pythonPackages)
              playwright-test
              gh
              # Formatting tools
              treefmt
              nodePackages.prettier
              ruff
            ];
            
            shellHook = ''
              echo "Setting up Playwright for macOS environment..."
              export PLAYWRIGHT_BROWSERS_PATH="${playwright-browsers-chromium}"
              
              export OPENAI_API_KEY=$(cat .secrets/openai-api-key)
              export ELEVEN_API_KEY=$(cat .secrets/eleven-api-key)
              export ABS_API_KEY=$(cat .secrets/abs-api-key)
              export ABS_URL=$(cat .secrets/abs-url)
            '';
          };
      })
    );
}
