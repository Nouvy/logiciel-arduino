#!/usr/bin/env python3
"""
Arduino Assistant - App graphique pour programmer un Arduino avec l'IA.
Les eleves decrivent ce qu'ils veulent en francais, l'IA genere le code,
et l'app compile + upload automatiquement sur l'Arduino.
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import threading
import re
import os
import tempfile
import shutil

ARDUINO_CLI = shutil.which("arduino-cli") or "/opt/homebrew/bin/arduino-cli"

# --- Charte graphique CESI ---
CESI_YELLOW = "#fbe216"
CESI_DARK = "#1a1a1a"
CESI_BLACK = "#000000"
CESI_WHITE = "#ffffff"
CESI_GRAY_BG = "#f5f5f5"
CESI_GRAY_TEXT = "#526e7a"
CESI_GRAY_BORDER = "#e0e0e0"
CESI_GREEN = "#2e7d32"
CESI_RED = "#c62828"
CESI_YELLOW_HOVER = "#e6cf00"


class ArduinoAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("Arduino Assistant - CESI")
        self.root.geometry("860x760")
        self.root.configure(bg=CESI_WHITE)
        self.root.minsize(700, 600)

        self.board_fqbn = None
        self.board_port = None

        style = {"bg": CESI_WHITE, "fg": CESI_DARK, "font": ("Helvetica", 13)}
        entry_style = {"bg": CESI_GRAY_BG, "fg": CESI_DARK, "insertbackground": CESI_DARK,
                        "font": ("Helvetica", 13), "relief": "solid", "bd": 1,
                        "highlightthickness": 2, "highlightcolor": CESI_YELLOW,
                        "highlightbackground": CESI_GRAY_BORDER}

        # --- Yellow top bar ---
        top_bar = tk.Frame(root, bg=CESI_YELLOW, height=6)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        # --- Header ---
        header = tk.Frame(root, bg=CESI_WHITE)
        header.pack(fill="x", padx=24, pady=(18, 8))
        tk.Label(header, text="ARDUINO", font=("Helvetica", 26, "bold"),
                 bg=CESI_WHITE, fg=CESI_DARK).pack(side="left")
        tk.Label(header, text=" ASSISTANT", font=("Helvetica", 26),
                 bg=CESI_WHITE, fg=CESI_GRAY_TEXT).pack(side="left")
        tk.Label(header, text="  CESI", font=("Helvetica", 14, "bold"),
                 bg=CESI_WHITE, fg=CESI_YELLOW).pack(side="left", padx=(10, 0))

        # --- Separator ---
        tk.Frame(root, bg=CESI_GRAY_BORDER, height=1).pack(fill="x", padx=24, pady=(0, 12))

        # --- API Key ---
        api_frame = tk.Frame(root, bg=CESI_WHITE)
        api_frame.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(api_frame, text="Cle API :", font=("Helvetica", 12, "bold"),
                 bg=CESI_WHITE, fg=CESI_DARK).pack(side="left")
        self.api_key_var = tk.StringVar()
        self.api_entry = tk.Entry(api_frame, textvariable=self.api_key_var, show="*",
                                   width=55, **entry_style)
        self.api_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # --- Board status ---
        board_frame = tk.Frame(root, bg=CESI_WHITE)
        board_frame.pack(fill="x", padx=24, pady=(0, 8))
        self.board_indicator = tk.Label(board_frame, text="\u25cf", font=("Helvetica", 14),
                                         bg=CESI_WHITE, fg=CESI_GRAY_TEXT)
        self.board_indicator.pack(side="left")
        self.board_label = tk.Label(board_frame, text="Arduino : recherche...",
                                     font=("Helvetica", 12), bg=CESI_WHITE, fg=CESI_GRAY_TEXT)
        self.board_label.pack(side="left", padx=(4, 0))
        self.detect_btn = tk.Button(board_frame, text="Detecter", command=self.detect_board,
                                     bg=CESI_DARK, fg=CESI_WHITE, font=("Helvetica", 11, "bold"),
                                     relief="flat", bd=0, padx=14, pady=4, cursor="hand2",
                                     activebackground="#333333", activeforeground=CESI_WHITE)
        self.detect_btn.pack(side="right")

        # --- Prompt ---
        tk.Label(root, text="Decris ce que tu veux que l'Arduino fasse :",
                 font=("Helvetica", 12, "bold"), bg=CESI_WHITE, fg=CESI_DARK
                 ).pack(anchor="w", padx=24, pady=(8, 4))
        self.prompt_text = scrolledtext.ScrolledText(root, height=4, wrap="word", **entry_style)
        self.prompt_text.pack(fill="x", padx=24, pady=(0, 8))

        # --- Main button ---
        btn_frame = tk.Frame(root, bg=CESI_WHITE)
        btn_frame.pack(fill="x", padx=24, pady=(0, 8))
        self.send_btn = tk.Button(btn_frame, text="GENERER ET ENVOYER SUR ARDUINO",
                                   command=self.on_send, bg=CESI_YELLOW, fg=CESI_BLACK,
                                   font=("Helvetica", 14, "bold"), relief="flat", bd=0,
                                   padx=20, pady=12, cursor="hand2",
                                   activebackground=CESI_YELLOW_HOVER,
                                   activeforeground=CESI_BLACK)
        self.send_btn.pack(fill="x")

        # --- Code display ---
        tk.Label(root, text="Code genere :", font=("Helvetica", 12, "bold"),
                 bg=CESI_WHITE, fg=CESI_DARK).pack(anchor="w", padx=24, pady=(8, 4))
        self.code_text = scrolledtext.ScrolledText(root, height=10, wrap="word",
                                                     bg=CESI_DARK, fg=CESI_YELLOW,
                                                     insertbackground=CESI_YELLOW,
                                                     selectbackground=CESI_YELLOW,
                                                     selectforeground=CESI_BLACK,
                                                     font=("Courier", 12), relief="solid", bd=1)
        self.code_text.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        # --- Log ---
        tk.Label(root, text="Journal :", font=("Helvetica", 12, "bold"),
                 bg=CESI_WHITE, fg=CESI_DARK).pack(anchor="w", padx=24, pady=(4, 4))
        self.log_text = scrolledtext.ScrolledText(root, height=5, wrap="word",
                                                    bg=CESI_GRAY_BG, fg=CESI_DARK,
                                                    font=("Courier", 11), relief="solid", bd=1)
        self.log_text.pack(fill="both", padx=24, pady=(0, 6))

        # --- Yellow bottom bar ---
        bottom_bar = tk.Frame(root, bg=CESI_YELLOW, height=4)
        bottom_bar.pack(fill="x", side="bottom")
        bottom_bar.pack_propagate(False)

        # Auto-detect board on start
        self.root.after(500, self.detect_board)

    def log(self, msg):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    def detect_board(self):
        self.board_label.config(text="Arduino : recherche...", fg=CESI_GRAY_TEXT)
        self.board_indicator.config(fg=CESI_GRAY_TEXT)
        threading.Thread(target=self._detect_board_thread, daemon=True).start()

    def _detect_board_thread(self):
        try:
            result = subprocess.run([ARDUINO_CLI, "board", "list"],
                                     capture_output=True, text=True, timeout=15)
            lines = result.stdout.strip().split("\n")
            for line in lines[1:]:
                if "arduino:" in line.lower():
                    parts = line.split()
                    port = parts[0]
                    fqbn_match = re.search(r'(arduino:\S+:\S+)', line)
                    if fqbn_match:
                        self.board_port = port
                        self.board_fqbn = fqbn_match.group(1)
                        name_match = re.search(r'(Arduino\s+\S+(?:\s+\S+)?)\s+arduino:', line)
                        name = name_match.group(1) if name_match else self.board_fqbn
                        self.root.after(0, lambda: self.board_label.config(
                            text=f"Arduino : {name} sur {self.board_port}", fg=CESI_GREEN))
                        self.root.after(0, lambda: self.board_indicator.config(fg=CESI_GREEN))
                        self.root.after(0, lambda: self.log(f"Board detecte : {name} sur {self.board_port}"))
                        return
            self.root.after(0, lambda: self.board_label.config(
                text="Arduino : non detecte - branche ton Arduino et clique Detecter", fg=CESI_RED))
            self.root.after(0, lambda: self.board_indicator.config(fg=CESI_RED))
            self.root.after(0, lambda: self.log("Aucun Arduino detecte."))
        except Exception as e:
            self.root.after(0, lambda: self.board_label.config(
                text=f"Erreur detection : {e}", fg=CESI_RED))
            self.root.after(0, lambda: self.board_indicator.config(fg=CESI_RED))

    def on_send(self):
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("Cle API manquante", "Entre ta cle API")
            return
        if not self.board_fqbn or not self.board_port:
            messagebox.showwarning("Arduino non detecte",
                                    "Branche ton Arduino et clique sur Detecter.")
            return
        prompt = self.prompt_text.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("Prompt vide", "Decris ce que tu veux que l'Arduino fasse !")
            return

        self.send_btn.config(state="disabled", text="EN COURS...", bg=CESI_GRAY_TEXT)
        self.code_text.delete("1.0", "end")
        self.log_text.delete("1.0", "end")
        threading.Thread(target=self._process, args=(api_key, prompt), daemon=True).start()

    def _process(self, api_key, prompt):
        try:
            self.root.after(0, lambda: self.log("Envoi de la demande a l'IA..."))
            code = self._ask_claude(api_key, prompt)
            if not code:
                self.root.after(0, lambda: self.log("ERREUR : l'IA n'a pas genere de code."))
                return
            self.root.after(0, lambda: self.code_text.insert("1.0", code))
            self.root.after(0, lambda: self.log("Code genere avec succes !"))

            self.root.after(0, lambda: self.log("Compilation en cours..."))
            sketch_dir = self._write_sketch(code)
            result = subprocess.run(
                [ARDUINO_CLI, "compile", "--fqbn", self.board_fqbn, sketch_dir],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                self.root.after(0, lambda: self.log(f"ERREUR compilation :\n{result.stderr}"))
                return
            self.root.after(0, lambda: self.log("Compilation OK !"))

            self.root.after(0, lambda: self.log("Upload sur l'Arduino..."))
            result = subprocess.run(
                [ARDUINO_CLI, "upload", "--fqbn", self.board_fqbn,
                 "--port", self.board_port, sketch_dir],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                self.root.after(0, lambda: self.log(f"ERREUR upload :\n{result.stderr}"))
                return
            self.root.after(0, lambda: self.log("Upload termine ! Ton Arduino execute le programme."))

        except Exception as e:
            self.root.after(0, lambda: self.log(f"ERREUR : {e}"))
        finally:
            self.root.after(0, lambda: self.send_btn.config(
                state="normal", text="GENERER ET ENVOYER SUR ARDUINO",
                bg=CESI_YELLOW))

    def _ask_claude(self, api_key, prompt):
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        system_prompt = (
            "Tu es un assistant Arduino. L'utilisateur decrit ce qu'il veut faire avec son Arduino. "
            f"Le board est un {self.board_fqbn}. "
            "Reponds UNIQUEMENT avec le code Arduino complet (fichier .ino), sans explication, "
            "sans markdown, sans balises de code. Juste le code C/C++ Arduino pret a compiler. "
            "Ajoute des commentaires en francais dans le code pour expliquer chaque partie."
        )
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        code = message.content[0].text.strip()
        code = re.sub(r'^```(?:cpp|c|arduino|ino)?\s*\n', '', code)
        code = re.sub(r'\n```\s*$', '', code)
        return code

    def _write_sketch(self, code):
        sketch_dir = os.path.join(tempfile.gettempdir(), "arduino_assistant_sketch")
        os.makedirs(sketch_dir, exist_ok=True)
        sketch_file = os.path.join(sketch_dir, "arduino_assistant_sketch.ino")
        with open(sketch_file, "w") as f:
            f.write(code)
        return sketch_dir


if __name__ == "__main__":
    root = tk.Tk()
    app = ArduinoAssistant(root)
    root.mainloop()
