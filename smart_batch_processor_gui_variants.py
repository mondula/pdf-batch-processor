import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from tkinter.simpledialog import askstring
import os

from pdf_to_prompt_variants import generate_format_prompt_for_variants, generate_extraction_prompt_for_pdf

from process_api_variants import process_with_gpt_two_calls

from export import export_to_csv
from pdf_to_prompt_variants import generate_format_prompt_for_variants
from field_registry import get_known_fields, update_fields

FIELD_POLICY_TEMPLATE = """You are extracting product variants into structured rows for a CSV/ERP import.

FIELD CONSISTENCY RULES:
- Prefer using existing field names from the global registry whenever they match the meaning.
- If the PDF contains information that does not fit any existing field, CREATE a new field.
- Do NOT rename existing fields just to make them look nicer. Keep them stable.
- Use consistent units and formats (e.g., bar, °C, DN, G 1/2).
- Missing values must be "N/A".

GLOBAL FIELD REGISTRY (use these keys when applicable):
{known_fields}

Now follow the manufacturer instructions below.
"""

class VariantExtractionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Manufacturer Variant Extraction")

        self.output_folder = ""

        # manufacturer -> base prompt text
        self.manufacturer_prompts = {}
        # manufacturer -> list[pdf_path]
        self.manufacturer_pdfs = {}

        # manufacturer selection
        self.current_mfr_var = tk.StringVar(value="(none)")

        # UI
        top = tk.Frame(root)
        top.pack(pady=10, anchor="w")

        tk.Button(top, text="Select Output Folder", command=self.set_output_folder).grid(row=0, column=0, padx=5)
        tk.Button(top, text="Add Manufacturer", command=self.add_manufacturer).grid(row=0, column=1, padx=5)
        tk.Button(top, text="Load Prompt (Current Mfr)", command=self.load_prompt_for_current).grid(row=0, column=2, padx=5)

        tk.Button(top, text="Add PDFs to Current Mfr", command=self.add_pdfs_to_current_mfr).grid(row=0, column=3, padx=5)
        tk.Button(top, text="Run Current Manufacturer", command=self.run_current_manufacturer).grid(row=0, column=4, padx=5)
        tk.Button(top, text="Run ALL Manufacturers", command=self.run_all_manufacturers).grid(row=0, column=5, padx=5)

        # Manufacturer picker
        mfr_frame = tk.Frame(root)
        mfr_frame.pack(anchor="w", padx=10)

        tk.Label(mfr_frame, text="Current Manufacturer:").pack(side=tk.LEFT)
        self.mfr_menu = tk.OptionMenu(mfr_frame, self.current_mfr_var, "(none)")
        self.mfr_menu.pack(side=tk.LEFT, padx=8)

        self.count_label = tk.Label(mfr_frame, text="PDFs: 0")
        self.count_label.pack(side=tk.LEFT, padx=12)

        # Log
        self.log = tk.Text(root, width=110, height=16, wrap=tk.WORD)
        self.log.pack(padx=10, pady=10)

        # Prompt editor
        tk.Label(root, text="Manufacturer Prompt (Current Manufacturer):").pack(anchor="w", padx=10)
        self.custom_prompt = ScrolledText(root, width=100, height=9)
        self.custom_prompt.pack(padx=10, pady=(0, 10))

        # CSV names
        bottom = tk.Frame(root)
        bottom.pack(anchor="w", padx=10, pady=(0, 10))

        tk.Label(bottom, text="Global combined CSV filename:").pack(side=tk.LEFT)
        self.global_csv_name = tk.StringVar(value="combined_variants_all.csv")
        tk.Entry(bottom, textvariable=self.global_csv_name, width=30).pack(side=tk.LEFT, padx=8)

        tk.Label(bottom, text="Per-manufacturer CSV filename suffix:").pack(side=tk.LEFT, padx=(20, 0))
        self.mfr_csv_suffix = tk.StringVar(value="_combined.csv")
        tk.Entry(bottom, textvariable=self.mfr_csv_suffix, width=18).pack(side=tk.LEFT, padx=8)

        self._refresh_mfr_menu()

    def log_message(self, msg: str):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def set_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.log_message(f"Output folder set: {folder}")

    def _refresh_mfr_menu(self):
        menu = self.mfr_menu["menu"]
        menu.delete(0, "end")

        options = ["(none)"] + sorted(self.manufacturer_prompts.keys())
        for opt in options:
            menu.add_command(label=opt, command=lambda v=opt: self._set_current_mfr(v))

        cur = self.current_mfr_var.get()
        if cur not in options:
            self._set_current_mfr("(none)")
        else:
            self._set_current_mfr(cur)

    def _set_current_mfr(self, name: str):
        self.current_mfr_var.set(name)

        if name in self.manufacturer_prompts:
            self.custom_prompt.delete("1.0", tk.END)
            self.custom_prompt.insert("1.0", self.manufacturer_prompts[name])
        else:
            self.custom_prompt.delete("1.0", tk.END)

        count = len(self.manufacturer_pdfs.get(name, [])) if name != "(none)" else 0
        self.count_label.config(text=f"PDFs: {count}")

    def add_manufacturer(self):
        name = askstring("Add Manufacturer", "Manufacturer name (e.g., Berluto, Götze, LESER):")
        if not name:
            return
        name = name.strip()
        if not name:
            return

        if name not in self.manufacturer_prompts:
            self.manufacturer_prompts[name] = ""
            self.manufacturer_pdfs[name] = []

        self._refresh_mfr_menu()
        self._set_current_mfr(name)
        self.log_message(f"Manufacturer added: {name}")

    def load_prompt_for_current(self):
        mfr = self.current_mfr_var.get()
        if mfr == "(none)":
            messagebox.showwarning("No Manufacturer", "Select or add a manufacturer first.")
            return


        prompt_file = filedialog.askopenfilename(
            title=f"Select Prompt File for {mfr}",
            filetypes=[("Text Files", "*.txt")]
        )
        if not prompt_file:
            return

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.manufacturer_prompts[mfr] = content
            self.custom_prompt.delete("1.0", tk.END)
            self.custom_prompt.insert("1.0", content)
            self.log_message(f"Loaded prompt for {mfr}: {os.path.basename(prompt_file)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load prompt: {e}")

    def add_pdfs_to_current_mfr(self):
        mfr = self.current_mfr_var.get()
        if mfr == "(none)":
            messagebox.showwarning("No Manufacturer", "Select or add a manufacturer first.")
            return

        files = filedialog.askopenfilenames(
            title=f"Select PDFs for {mfr}",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not files:
            return

        existing = set(self.manufacturer_pdfs.get(mfr, []))
        added = 0
        for f in files:
            if f not in existing:
                self.manufacturer_pdfs[mfr].append(f)
                added += 1

        self.count_label.config(text=f"PDFs: {len(self.manufacturer_pdfs[mfr])}")
        self.log_message(f"Added {added} PDF(s) to manufacturer {mfr}. Total now: {len(self.manufacturer_pdfs[mfr])}")

    def _build_prompt_for_run(self, manufacturer_base_prompt: str) -> str:
        known_fields = get_known_fields(self.output_folder) if self.output_folder else []
        known_fields_str = "\n".join(f"- {f}" for f in known_fields) if known_fields else "- (none yet)"

        field_policy = FIELD_POLICY_TEMPLATE.format(known_fields=known_fields_str)

        base = (manufacturer_base_prompt or "").strip()
        if not base:
            base = self.custom_prompt.get("1.0", tk.END).strip()

        master = generate_extraction_prompt_for_pdf()

        return (
                master
                + "\n\n"
                + field_policy
                + "\n\nMANUFACTURER INSTRUCTIONS:\n"
                + base
        )

    def _run_manufacturer(self, mfr: str, show_dialogs: bool = True):
        if mfr == "(none)":
            if show_dialogs:
                messagebox.showwarning("No Manufacturer", "Select a manufacturer first.")
            return
        if not self.output_folder:
            if show_dialogs:
                messagebox.showwarning("No Output Folder", "Please select an output folder.")
            return

        pdfs = self.manufacturer_pdfs.get(mfr, [])
        if not pdfs:
            if show_dialogs:
                messagebox.showwarning("No PDFs", f"No PDFs added for {mfr}.")
            return

        # Save current editor prompt into manufacturer prompt
        # Only do this for the currently-selected manufacturer.
        if self.current_mfr_var.get() == mfr:
            self.manufacturer_prompts[mfr] = self.custom_prompt.get("1.0", tk.END).strip()

        format_prompt = generate_format_prompt_for_variants()

        # Build final prompt with known fields included
        final_prompt = self._build_prompt_for_run(self.manufacturer_prompts.get(mfr, ""))

        self.log_message(f"\n=== Running manufacturer: {mfr} | PDFs: {len(pdfs)} ===")

        manufacturer_rows = []
        global_rows_path = os.path.join(self.output_folder, self.global_csv_name.get().strip() or "combined_variants_all.csv")

        for pdf_path in pdfs:
            filename = os.path.basename(pdf_path)
            base, _ = os.path.splitext(filename)
            self.log_message(f"Processing: {filename}")

            try:
                variants = process_with_gpt_two_calls(
                    pdf_path,
                    custom_prompt=final_prompt,
                    format_prompt=format_prompt
                )

                if not variants:
                    self.log_message("No variant rows returned.")
                    continue

                # Add meta fields (kept as strings for CSV export)
                for r in variants:
                    if isinstance(r, dict):
                        r["Manufacturer"] = mfr
                        r["Source PDF"] = filename
                        r["Source PDF Path"] = pdf_path

                # Update registry with newly seen keys
                new_fields = update_fields(self.output_folder, [r for r in variants if isinstance(r, dict)])
                if new_fields:
                    self.log_message(f"New fields discovered: {', '.join(new_fields)}")

                # Save per-PDF CSV
                per_pdf_csv = os.path.join(self.output_folder, f"{mfr}__{base}_variants.csv")
                export_to_csv(variants, per_pdf_csv)
                self.log_message(f"Saved per PDF CSV: {per_pdf_csv}")

                manufacturer_rows.extend([r for r in variants if isinstance(r, dict)])

            except Exception as e:
                self.log_message(f"Error processing {filename}: {e}")

        # Save manufacturer combined CSV
        if manufacturer_rows:
            mfr_combined_name = f"{mfr}{self.mfr_csv_suffix.get().strip() or '_combined.csv'}"
            mfr_combined_path = os.path.join(self.output_folder, mfr_combined_name)
            export_to_csv(manufacturer_rows, mfr_combined_path)
            self.log_message(f" Manufacturer combined CSV saved: {mfr_combined_path}")

            # Append into global CSV
            global_rows = []
            if os.path.exists(global_rows_path):
                try:
                    import pandas as pd
                    df_old = pd.read_csv(global_rows_path, dtype=str, keep_default_na=False)
                    global_rows = df_old.to_dict(orient="records")
                except Exception:
                    global_rows = []

            global_rows.extend(manufacturer_rows)
            export_to_csv(global_rows, global_rows_path)
            self.log_message(f" Global combined CSV updated: {global_rows_path}")

        else:
            self.log_message("No rows extracted for this manufacturer.")

        self.log_message(f"=== Done: {mfr} ===\n")

    def run_current_manufacturer(self):
        mfr = self.current_mfr_var.get()
        self._run_manufacturer(mfr, show_dialogs=True)

    def run_all_manufacturers(self):
        if not self.output_folder:
            messagebox.showwarning("No Output Folder", "Please select an output folder.")
            return

        manufacturers = sorted([m for m in self.manufacturer_prompts.keys() if m and m != "(none)"])
        if not manufacturers:
            messagebox.showwarning("No Manufacturers", "No manufacturers added.")
            return

        self.log_message(f"\n=== Running ALL manufacturers: {len(manufacturers)} ===")
        for mfr in manufacturers:
            if not self.manufacturer_pdfs.get(mfr, []):
                self.log_message(f"Skipping {mfr}: no PDFs")
                continue
            self.current_mfr_var.set(mfr)
            self._run_manufacturer(mfr, show_dialogs=False)

        self.log_message("=== Done: ALL manufacturers ===\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = VariantExtractionApp(root)
    root.mainloop()
