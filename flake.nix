{
  description = "TicketSeller Python and PyQt6 development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;

      mkPkgs = system: import nixpkgs { inherit system; };

      mkPython = pkgs: pkgs.python311.withPackages (pythonPackages: [
        pythonPackages.pyqt6
      ]);

      mkTicketSellerApp = system: mode:
        let
          pkgs = mkPkgs system;
          python = mkPython pkgs;
          script = pkgs.writeShellApplication {
            name = "ticketseller-${mode}";
            runtimeInputs = [ python ];
            text = ''
              export PYTHONPATH="${self}/src''${PYTHONPATH:+:$PYTHONPATH}"
              exec python -m ticketseller.app ${mode} "$@"
            '';
          };
        in
        {
          type = "app";
          program = "${script}/bin/ticketseller-${mode}";
        };

      mkTicketSellerTests = system:
        let
          pkgs = mkPkgs system;
          python = mkPython pkgs;
          script = pkgs.writeShellApplication {
            name = "ticketseller-tests";
            runtimeInputs = [ python ];
            text = ''
              export PYTHONPATH="${self}/src''${PYTHONPATH:+:$PYTHONPATH}"
              exec python -m unittest discover -s "${self}/tests" "$@"
            '';
          };
        in
        {
          type = "app";
          program = "${script}/bin/ticketseller-tests";
        };
    in
    {
      apps = forAllSystems (system: {
        default = mkTicketSellerApp system "kiosk";
        kiosk = mkTicketSellerApp system "kiosk";
        clerk = mkTicketSellerApp system "clerk";
        tests = mkTicketSellerTests system;
      });

      devShells = forAllSystems (system:
        let
          pkgs = mkPkgs system;
          python = mkPython pkgs;
        in
        {
          default = pkgs.mkShell {
            packages = [
              python
              pkgs.zip
            ];

            shellHook = ''
              export PYTHONPATH="$PWD/src''${PYTHONPATH:+:$PYTHONPATH}"
              echo "TicketSeller development shell"
              echo "Run tests: python -m unittest discover -s tests"
              echo "Run GUI:   python -m ticketseller.app kiosk"
            '';
          };
        });
    };
}
