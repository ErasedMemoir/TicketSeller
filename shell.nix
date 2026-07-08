{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = [
    (pkgs.python311.withPackages (pythonPackages: [
      pythonPackages.pyqt6
    ]))
    pkgs.zip
  ];
}
