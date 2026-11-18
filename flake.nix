{
    description = "Ticketseller Python Environment";

    inputs = {
        nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";     
    };

    outputs = { self, nixpkgs}:
        let
            system = "x86_64-linux";
            pkgs = nixpkgs.legacyPackages.${system};

            pythonEnv = pkgs.python3.withPackages (ps: with ps; [
                pyqt6
            ]);
        in
        {
            devShells.${system}.default = pkgs.mkShell {
                packages = [
                    pythonEnv
                    pkgs.qt6.qtwayland
                ];

                shellHook = ''
                    export PYTHONPATH="$PWD/src:$PYTHONPATH"
                    echo "Flake activated."
                    echo "To run kiosk: python -m ticketseller.app kiosk"
                    echo "To run clerk: python -m ticketseller.app clerk"
                '';
            };
        };
}