{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
    buildInputs = [
        (pkgs.python3.withPackages (ps: with ps; [ pyqt6 ]))
        pkgs.qt6.qtwayland
    ];
    shellHook = ''
        export PYTHONPATH="$PWD/src:$PYTHONPATH"
        echo "nix-shell activated successfully."
        echo "To run kiosk: python -m ticketseller.app kiosk"
        echo "To run clerk: python -m ticketseller.app clerk"
    '';
}