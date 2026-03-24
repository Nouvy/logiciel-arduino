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

class ArduinoAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("Arduino Assistant")
        self.root.geometry("820x720")
        self.root.configure(bg="#1e1e2e")

        self.board_fqbn = None
        self.board_port = None

        style = {"bg": "#1e1e2e", "fg": "#cdd6f4", "font": ("Helvetica", 13)}
        entry_style = {"bg": "#313244", "fg": "#cdd6f4", "insertbackground": "#cdd6f4",
                        "font": ("Helvetica", 13), "relief": "flat", "bd": 8}

        # --- Header ---
        header = tk.Frame(root, bg="#1e1e2e")
        header.pack(fill="x", padx=20, pady=(15, 5))
        tk.Label(header, text="Arduino Assistant", font=("Helvetica", 22, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(side="left")

        # --- API Key ---
        api_frame = tk.Frame(root, bg="#1e1e2e")
        api_frame.pack(fill="x", padx=20, pady=(5, 5))
        tk.Label(api_frame, text="Cle API :", **style).pack(side="left")
        self.api_key_var = tk.StringVar()
        self.api_entry = tk.Entry(api_frame, textvariable=self.api_key_var, show="*",
                                   width=50, **entry_style)
        self.api_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # --- Board status ---
        board_frame = tk.Frame(root, bg="#1e1e2e")
        board_frame.pack(fill="x", padx=20, pady=(5, 5))
        self.board_label = tk.Label(board_frame, text="Arduino : recherche...",
                                     font=("Helvetica", 12), bg="#1e1e2e", fg="#a6adc8")
        self.board_label.pack(side="left")
        self.detect_btn = tk.Button(board_frame, text="Detecter", command=self.detect_board,
                                     bg="#45475a", fg="#cdd6f4", font=("Helvetica", 11),
                                     relief="flat", bd=4, cursor="hand2")
        self.detect_btn.pack(side="right")

        # --- Prompt ---
        tk.Label(root, text="Decris ce que tu veux que l'Arduino fasse :",
                 **style).pack(anchor="w", padx=20, pady=(10, 3))
        self.prompt_text = scrolledtext.ScrolledText(root, height=5, wrap="word", **entry_style)
        self.prompt_text.pack(fill="x", padx=20, pady=(0, 5))

        # --- Buttons ---
        btn_frame = tk.Frame(root, bg="#1e1e2e")
        btn_frame.pack(fill="x", padx=20, pady=5)
        self.send_btn = tk.Button(btn_frame, text="Generer et Envoyer sur Arduino",
                                   command=self.on_send, bg="#89b4fa", fg="#1e1e2e",
                                   font=("Helvetica", 14, "bold"), relief="flat", bd=6,
                                   cursor="hand2", activebackground="#74c7ec")
        self.send_btn.pack(fill="x")

        # --- Code display ---
        tk.Label(root, text="Code genere :", **style).pack(anchor="w", padx=20, pady=(10, 3))
        self.code_text = scrolledtext.ScrolledText(root, height=10, wrap="word",
                                                     bg="#181825", fg="#a6e3a1",
                                                     insertbackground="#a6e3a1",
                                                     font=("Courier", 12), relief="flat", bd=8)
        self.code_text.pack(fill="both", expand=True, padx=20, pady=(0, 5))

        # --- Log ---
        tk.Label(root, text="Journal :", **style).pack(anchor="w", padx=20, pady=(5, 3))
        self.log_text = scrolledtext.ScrolledText(root, height=6, wrap="word",
                                                    bg="#181825", fg="#fab387",
                                                    font=("Courier", 11), relief="flat", bd=8)
        self.log_text.pack(fill="both", padx=20, pady=(0, 15))

        # Auto-detect board on start
        self.root.after(500, self.detect_board)

    def log(self, msg):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    def detect_board(self):
        self.board_label.config(text="Arduino : recherche...", fg="#a6adc8")
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
                    # Find FQBN (looks like arduino:something:something)
                    fqbn_match = re.search(r'(arduino:\S+:\S+)', line)
                    if fqbn_match:
                        self.board_port = port
                        self.board_fqbn = fqbn_match.group(1)
                        # Find board name
                        name_match = re.search(r'(Arduino\s+\S+(?:\s+\S+)?)\s+arduino:', line)
                        name = name_match.group(1) if name_match else self.board_fqbn
                        self.root.after(0, lambda: self.board_label.config(
                            text=f"Arduino : {name} sur {self.board_port}", fg="#a6e3a1"))
                        self.root.after(0, lambda: self.log(f"Board detecte : {name} sur {self.board_port}"))
                        return
            self.root.after(0, lambda: self.board_label.config(
                text="Arduino : non detecte - branche ton Arduino et clique Detecter", fg="#f38ba8"))
            self.root.after(0, lambda: self.log("Aucun Arduino detecte."))
        except Exception as e:
            self.root.after(0, lambda: self.board_label.config(
                text=f"Erreur detection : {e}", fg="#f38ba8"))

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

        self.send_btn.config(state="disabled", text="En cours...")
        self.code_text.delete("1.0", "end")
        self.log_text.delete("1.0", "end")
        threading.Thread(target=self._process, args=(api_key, prompt), daemon=True).start()

    def _process(self, api_key, prompt):
        try:
            # Step 1: Generate code with Claude
            self.root.after(0, lambda: self.log("Envoi de la demande a l'IA..."))
            code = self._ask_claude(api_key, prompt)
            if not code:
                self.root.after(0, lambda: self.log("ERREUR : l'IA n'a pas genere de code."))
                return
            self.root.after(0, lambda: self.code_text.insert("1.0", code))
            self.root.after(0, lambda: self.log("Code genere avec succes !"))

            # Step 2: Compile
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

            # Step 3: Upload
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
                state="normal", text="Generer et Envoyer sur Arduino"))

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
        # Clean up markdown fences if present
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
