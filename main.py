import tkinter as tk

from Pokemon import PokemonToolsApp


def main() -> None:
    root = tk.Tk()
    app = PokemonToolsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

