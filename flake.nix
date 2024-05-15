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
              python311Packages.beautifulsoup4
              python311Packages.click
              python311Packages.openai
              python311Packages.pydub
              python311Packages.pytest
              python311Packages.readability-lxml
              python311Packages.requests
            ];
            shellHook = ''
              $SHELL
            '';
          };
        }
      );
}
