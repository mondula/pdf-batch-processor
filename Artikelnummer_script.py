import pandas as pd
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox

def extract_numbers_from_path(path: str):
    """
    Expected filename pattern: '052030 - 031.pdf' somewhere in name.
    Returns (perlwitz, hersteller) or N/A if no match.
    """
    if not isinstance(path, str) or not path.strip():
        return "N/A", "N/A"

    filename = os.path.basename(path.strip())
    m = re.search(r"(\d+)\s*-\s*(\d+)", filename)
    if not m:
        return "N/A", "N/A"
    return m.group(1), m.group(2)

def default_output_path(input_path: str) -> str:
    if not input_path.lower().endswith(".csv"):
        return input_path + "_fixed.csv"
    return input_path[:-4] + "_fixed.csv"

class CsvFixGui:
    #gui
    def __init__(self, root):
        self.root = root
        self.root.title("Perlwitz Artikelnummer Fixer")

        self.in_path = tk.StringVar(value="")
        self.out_path = tk.StringVar(value="")

        frm = tk.Frame(root, padx=12, pady=12)
        frm.pack(fill="both", expand=True)

        # Input
        tk.Label(frm, text="Input CSV:").grid(row=0, column=0, sticky="w")
        tk.Entry(frm, textvariable=self.in_path, width=60).grid(row=1, column=0, padx=(0, 8), sticky="we")
        tk.Button(frm, text="Auswählen…", command=self.pick_input).grid(row=1, column=1, sticky="e")

        # Output
        tk.Label(frm, text="Output CSV (optional):").grid(row=2, column=0, pady=(10, 0), sticky="w")
        tk.Entry(frm, textvariable=self.out_path, width=60).grid(row=3, column=0, padx=(0, 8), sticky="we")
        tk.Button(frm, text="Speichern als…", command=self.pick_output).grid(row=3, column=1, sticky="e")

        # Options
        self.write_hersteller = tk.BooleanVar(value=True)
        tk.Checkbutton(
            frm,
            text="Auch Hersteller_Artikelnummer schreiben (aus Dateiname)",
            variable=self.write_hersteller
        ).grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky="w")

        # Run
        tk.Button(frm, text="Fix ausführen", command=self.run_fix, height=2).grid(
            row=5, column=0, columnspan=2, pady=(14, 0), sticky="we"
        )

        frm.columnconfigure(0, weight=1)

    def pick_input(self):
        path = filedialog.askopenfilename(
            title="Input CSV auswählen",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.in_path.set(path)
            # suggest default output
            if not self.out_path.get().strip():
                self.out_path.set(default_output_path(path))

    def pick_output(self):
        path = filedialog.asksaveasfilename(
            title="Output CSV speichern",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.out_path.set(path)

    def run_fix(self):
        in_csv = self.in_path.get().strip()
        out_csv = self.out_path.get().strip()


        if not os.path.exists(in_csv):
            messagebox.showerror("Nicht gefunden", f"Input-CSV nicht gefunden:\n{in_csv}")
            return

        if not out_csv:
            out_csv = default_output_path(in_csv)
            self.out_path.set(out_csv)

        try:
            df = pd.read_csv(in_csv, dtype=str, keep_default_na=False)
        except Exception as e:
            messagebox.showerror("Lesefehler", f"CSV konnte nicht gelesen werden:\n{e}")
            return

        if "Source PDF Path" not in df.columns:
            messagebox.showerror(
                "Spalte fehlt",
                "Die Spalte 'Source PDF Path' wurde nicht gefunden.\n"
                "Bitte prüfen, ob du die richtige CSV ausgewählt hast."
            )
            return

        perlwitz_vals = []
        hersteller_vals = []

        for p in df["Source PDF Path"].tolist():
            perlwitz, hersteller = extract_numbers_from_path(p)
            perlwitz_vals.append(perlwitz)
            hersteller_vals.append(hersteller)

        df["Perlwitz_Artikelnummer"] = perlwitz_vals
        if self.write_hersteller.get():
            df["Hersteller_Artikelnummer"] = hersteller_vals

        # quick stats
        filled = sum(1 for x in perlwitz_vals if x != "N/A")
        total = len(perlwitz_vals)

        try:
            df.to_csv(out_csv, index=False, encoding="utf-8")
        except Exception as e:
            messagebox.showerror("Schreibfehler", f"Out CSV konnte nicht gespeichert werden:\n{e}")
            return

        messagebox.showinfo(
            "Fertig",
            f"Gespeichert:\n{out_csv}\n\n"
            f"Perlwitz_Artikelnummer gefüllt: {filled}/{total}\n"
            f"Nicht erkannt: {total - filled} (bleibt 'N/A')"
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = CsvFixGui(root)
    root.mainloop()
