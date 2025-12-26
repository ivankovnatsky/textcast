{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/6bd7ba77ef6015853d67a89bd59f01b2880e9050";
    flake-utils.url = "github:numtide/flake-utils/11707dc2f618dd54ca8739b309ec4fc024de578b";
  };
  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ (final: prev: { }) ];
        };

        # Determine platform
        isLinux = pkgs.stdenv.hostPlatform.isLinux;
        isDarwin = pkgs.stdenv.hostPlatform.isDarwin;

        # Common Python packages for both platforms
        # NOTE: Keep in sync with pyproject.toml [tool.poetry.dependencies]
        # TODO: Migrate to poetry2nix when riscv64 support is fixed
        pythonPackages =
          ps: with ps; [
            # Core Dependencies
            anthropic
            beautifulsoup4
            click
            elevenlabs
            feedparser
            flask
            lxml
            openai
            playwright
            pydub
            pyyaml
            readability-lxml
            requests
            watchdog
            yt-dlp
            # Development & Testing
            pytest
            requests-mock
            cogapp
            # Code Quality
            autoflake
          ];

        # Python environment with all dependencies
        pythonEnv = pkgs.python312.withPackages pythonPackages;

        # Package the service
        textcastPackage = pkgs.python312Packages.buildPythonApplication {
          pname = "textcast";
          version = "0.1.0";
          pyproject = true;

          src = ./.;

          nativeBuildInputs = [ pkgs.makeWrapper ];

          buildInputs = [
            pkgs.coreutils
            pkgs.ffmpeg
            pkgs.playwright-driver.browsers
          ];

          build-system = with pkgs.python312Packages; [
            poetry-core
          ];

          dependencies = pythonPackages pkgs.python312Packages;

          # Disable runtime dependency check - simpleaudio is optional (Darwin-only)
          # and causes platform issues by pulling in alsa-lib (Linux-only)
          dontCheckRuntimeDeps = true;

          postFixup = ''
            wrapProgram $out/bin/textcast \
              --prefix PATH : "${
                pkgs.lib.makeBinPath [
                  pkgs.coreutils
                  pkgs.ffmpeg
                ]
              }" \
              --set PLAYWRIGHT_BROWSERS_PATH "${pkgs.playwright-driver.browsers}" \
              --set PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS "true"
          '';

          meta = with pkgs.lib; {
            description = "Text to Audio Podcast Service";
            homepage = "https://github.com/ivankovnatsky/textcast";
            license = licenses.mit;
          };
        };
      in
      # Linux-specific configuration
      (
        if isLinux then
          {
            packages = {
              textcast = textcastPackage;
              default = textcastPackage;
            };

            devShells.default = pkgs.mkShell {
              buildInputs = with pkgs; [
                coreutils
                ffmpeg
                pythonEnv
                playwright-test
                playwright-driver.browsers
                gh
                # Formatting tools
                treefmt
                nodePackages.prettier
                nixfmt-rfc-style
                ruff
              ];

              shellHook = ''
                echo "Setting up Playwright for Linux environment..."
                export PATH="${pkgs.coreutils}/bin:${pkgs.ffmpeg}/bin:$PATH"
                export PLAYWRIGHT_BROWSERS_PATH="${pkgs.playwright-driver.browsers}"
                export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

                export OPENAI_API_KEY=$(cat .secrets/openai-api-key)
                export ELEVEN_API_KEY=$(cat .secrets/eleven-api-key)
                export ABS_API_KEY=$(cat .secrets/abs-api-key)
                export ABS_URL=$(cat .secrets/abs-url)
              '';
            };
          }
        # macOS-specific configuration
        else
          {
            packages = {
              textcast = textcastPackage;
              default = textcastPackage;
            };

            devShells.default = pkgs.mkShell {
              buildInputs = with pkgs; [
                coreutils
                ffmpeg
                pythonEnv
                playwright-test
                playwright-driver.browsers
                gh
                # Formatting tools
                treefmt
                nodePackages.prettier
                nixfmt-rfc-style
                ruff
              ];

              shellHook = ''
                echo "Setting up Playwright for macOS environment..."
                export PATH="${pkgs.coreutils}/bin:${pkgs.ffmpeg}/bin:$PATH"
                export PLAYWRIGHT_BROWSERS_PATH="${pkgs.playwright-driver.browsers}"
                export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

                export OPENAI_API_KEY=$(cat .secrets/openai-api-key)
                export ELEVEN_API_KEY=$(cat .secrets/eleven-api-key)
                export ABS_API_KEY=$(cat .secrets/abs-api-key)
                export ABS_URL=$(cat .secrets/abs-url)
              '';
            };
          }
      )
    );
}
