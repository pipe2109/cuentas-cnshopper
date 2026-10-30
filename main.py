import os
import sqlite3
import shutil
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from browser_session import launch_browser
from database import (db, init_db, make_backup, start_registration, change_registration,
                      latest_registration, registration_history, REGISTRATION_STATES)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
BACKUP_DIR = os.path.join(APP_DIR, "backups")
DB_PATH = os.path.join(DATA_DIR, "clients.db")
REGISTRATION_URL = "https://cnshopper.com/?invite_id=2370842&promoter_id=2370842"
STATUSES = ["Pendiente", "En proceso", "Completado", "En espera"]

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CNShopper Client Assistant")
        self.geometry("1180x780")
        self.minsize(980, 680)
        self.configure(fg_color="#101722")
        self.selected_id = None
        init_db()
        self.build()
        self.refresh()

    def build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        side = ctk.CTkFrame(self, width=225, corner_radius=0, fg_color="#151F2E")
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        ctk.CTkLabel(side, text="CNShopper", font=ctk.CTkFont(size=25, weight="bold")).pack(anchor="w", padx=22, pady=(30, 2))
        ctk.CTkLabel(side, text="CLIENT ASSISTANT  •  V4.1", text_color="#8FA3BC",
                     font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=23)
        ctk.CTkFrame(side, height=2, fg_color="#29384C").pack(fill="x", padx=20, pady=25)
        ctk.CTkButton(side, text="  Gestión de clientes", anchor="w", height=42,
                      fg_color="#245C91").pack(fill="x", padx=15)
        ctk.CTkButton(side, text="  Abrir CNShopper", anchor="w", height=42,
                      fg_color="transparent", hover_color="#24354A",
                      command=lambda: self.open_cnshopper()).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(side, text="  Abrir carpeta de respaldos", anchor="w", height=42,
                      fg_color="transparent", hover_color="#24354A",
                      command=self.open_backups).pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(side, text="Los respaldos se guardan\nlocalmente en /backups.\nNo almacenes contraseñas,\nOTP ni datos de pago.",
                     justify="left", text_color="#8FA3BC", font=ctk.CTkFont(size=11)
                     ).pack(side="bottom", anchor="w", padx=20, pady=25)

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=26, pady=22)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(main, text="Panel de clientes", font=ctk.CTkFont(size=28, weight="bold")
                     ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(main, text="Datos de contacto, estados y actividad reciente.",
                     text_color="#9AABC0").grid(row=0, column=0, sticky="w", pady=(42, 0))

        stats = ctk.CTkFrame(main, fg_color="transparent")
        stats.grid(row=1, column=0, sticky="ew", pady=(18, 15))
        self.stats = {}
        for key, title in [("total", "Total"), ("pending", "Pendientes"),
                           ("process", "En proceso"), ("done", "Completados")]:
            box = ctk.CTkFrame(stats, fg_color="#192536", corner_radius=12)
            box.pack(side="left", expand=True, fill="x", padx=(0, 9))
            ctk.CTkLabel(box, text=title, text_color="#9AABC0").pack(anchor="w", padx=14, pady=(10, 0))
            value = ctk.CTkLabel(box, text="0", font=ctk.CTkFont(size=24, weight="bold"))
            value.pack(anchor="w", padx=14, pady=(0, 10))
            self.stats[key] = value

        form = ctk.CTkFrame(main, fg_color="#192536", corner_radius=14)
        form.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        form.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkLabel(form, text="Ficha del cliente", font=ctk.CTkFont(size=17, weight="bold")
                     ).grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(13, 7))
        self.name = ctk.CTkEntry(form, placeholder_text="Nombre completo", height=36)
        self.email = ctk.CTkEntry(form, placeholder_text="Correo de contacto", height=36)
        self.phone = ctk.CTkEntry(form, placeholder_text="Teléfono / contacto", height=36)
        self.name.grid(row=1, column=0, sticky="ew", padx=(16, 5), pady=5)
        self.email.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.phone.grid(row=1, column=2, sticky="ew", padx=(5, 16), pady=5)
        self.notes = ctk.CTkEntry(form, placeholder_text="Observaciones (no contraseñas ni códigos)", height=36)
        self.notes.grid(row=2, column=0, columnspan=2, sticky="ew", padx=(16, 5), pady=5)
        self.status = ctk.CTkOptionMenu(form, values=STATUSES, height=36)
        self.status.grid(row=2, column=2, sticky="ew", padx=(5, 16), pady=5)
        btns = ctk.CTkFrame(form, fg_color="transparent")
        btns.grid(row=3, column=0, columnspan=3, sticky="ew", padx=12, pady=(7, 12))
        ctk.CTkButton(btns, text="＋ Agregar cliente", width=130, command=self.add).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Guardar cambios", width=130, fg_color="#286B59",
                      hover_color="#32846D", command=self.update).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Limpiar", width=90, fg_color="#40516A",
                      command=self.clear).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Actividad reciente", width=140, fg_color="#40516A",
                      command=self.recent_activity).pack(side="right", padx=4)

        toolbar = ctk.CTkFrame(main, fg_color="transparent")
        toolbar.grid(row=3, column=0, sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)
        self.search = ctk.CTkEntry(toolbar, placeholder_text="Buscar por nombre, correo o teléfono...", height=36)
        self.search.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search.bind("<KeyRelease>", lambda _e: self.refresh())
        ctk.CTkButton(toolbar, text="Actualizar", width=100, command=self.refresh).grid(row=0, column=1)

        tracking = ctk.CTkFrame(main, fg_color="#192536", corner_radius=12)
        tracking.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        self.tracking_label = ctk.CTkLabel(tracking, text="Registro asistido: selecciona un cliente",
                                           font=ctk.CTkFont(size=13, weight="bold"))
        self.tracking_label.pack(side="left", padx=12, pady=9)
        ctk.CTkButton(tracking, text="Iniciar registro", width=120,
                      command=self.begin_registration).pack(side="right", padx=7)
        ctk.CTkButton(tracking, text="Seguimiento", width=105, fg_color="#40516A",
                      command=self.open_tracking).pack(side="right", padx=4)
        self.listbox = ctk.CTkScrollableFrame(main, fg_color="#192536", corner_radius=14)
        self.listbox.grid(row=5, column=0, sticky="nsew", pady=(10, 0))
        ctk.CTkLabel(main, text="Los datos se guardan en tu PC. El respaldo automático conserva hasta 20 copias.",
                     text_color="#8195AD", font=ctk.CTkFont(size=10)
                     ).grid(row=6, column=0, sticky="w", pady=(9, 0))

    def log(self, cid, action, details=""):
        with db() as con:
            con.execute("INSERT INTO client_history(client_id, action, details) VALUES(?,?,?)",
                        (cid, action, details))

    def values(self):
        return (self.name.get().strip(), self.email.get().strip(), self.phone.get().strip(),
                self.status.get(), self.notes.get().strip())

    def add(self):
        name, email, phone, status, notes = self.values()
        if not name or not (email or phone):
            messagebox.showwarning("Faltan datos", "Indica el nombre y al menos un correo o teléfono.")
            return
        with db() as con:
            cur = con.execute("""INSERT INTO clients(name, contact, email, phone, status, notes)
                                 VALUES(?,?,?,?,?,?)""",
                              (name, email or phone, email, phone, status, notes))
            cid = cur.lastrowid
        self.log(cid, "Cliente agregado", f"Estado inicial: {status}")
        self.clear()
        self.refresh()

    def update(self):
        if self.selected_id is None:
            messagebox.showinfo("Selecciona un cliente", "Pulsa Editar en una ficha.")
            return
        name, email, phone, status, notes = self.values()
        if not name or not (email or phone):
            messagebox.showwarning("Faltan datos", "Indica el nombre y al menos un correo o teléfono.")
            return
        with db() as con:
            con.execute("""UPDATE clients SET name=?, contact=?, email=?, phone=?, status=?,
                           notes=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                        (name, email or phone, email, phone, status, notes, self.selected_id))
        self.log(self.selected_id, "Ficha actualizada", f"Estado: {status}")
        self.clear()
        self.refresh()

    def select(self, cid):
        with db() as con:
            row = con.execute("SELECT name,email,phone,status,notes,contact FROM clients WHERE id=?",
                              (cid,)).fetchone()
        if not row:
            return
        self.selected_id = cid
        vals = [row[0], row[1] or row[5] or "", row[2] or "", row[4] or ""]
        for widget, value in zip((self.name, self.email, self.phone, self.notes), vals):
            widget.delete(0, "end")
            widget.insert(0, value)
        self.status.set(row[3])
        self.update_tracking_label()

    def clear(self):
        self.selected_id = None
        for w in (self.name, self.email, self.phone, self.notes):
            w.delete(0, "end")
        self.status.set("Pendiente")
        self.update_tracking_label()

    def delete(self, cid):
        if not messagebox.askyesno("Confirmar", "¿Eliminar cliente e historial?"):
            return
        with db() as con:
            con.execute("DELETE FROM registration_history WHERE client_id=?", (cid,))
            con.execute("DELETE FROM client_history WHERE client_id=?", (cid,))
            con.execute("DELETE FROM clients WHERE id=?", (cid,))
        self.clear()
        self.refresh()

    def recent_activity(self):
        with db() as con:
            rows = con.execute("""SELECT c.name,h.action,h.details,h.created_at
                                  FROM client_history h JOIN clients c ON c.id=h.client_id
                                  ORDER BY h.id DESC LIMIT 50""").fetchall()
        win = ctk.CTkToplevel(self)
        win.title("Actividad reciente")
        win.geometry("700x480")
        win.configure(fg_color="#101722")
        ctk.CTkLabel(win, text="Actividad reciente", font=ctk.CTkFont(size=21, weight="bold")
                     ).pack(anchor="w", padx=18, pady=15)
        frame = ctk.CTkScrollableFrame(win, fg_color="#192536")
        frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        if not rows:
            ctk.CTkLabel(frame, text="Todavía no hay actividad.").pack(pady=25)
        for name, action, details, created in rows:
            ctk.CTkLabel(frame, text=f"{created}  •  {name}  •  {action}",
                         font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 2))
            if details:
                ctk.CTkLabel(frame, text=details, text_color="#AABBD0").pack(anchor="w", padx=10)

    def update_tracking_label(self):
        if not hasattr(self, 'tracking_label'):
            return
        if self.selected_id is None:
            self.tracking_label.configure(text="Registro asistido: selecciona un cliente")
        else:
            attempt = latest_registration(self.selected_id)
            state = attempt[1] if attempt else 'No iniciado'
            self.tracking_label.configure(text=f"Cliente #{self.selected_id}  •  Registro: {state}")

    def open_cnshopper(self, cid=None, attempt_id=None):
        # Preguntar siempre: el modo se elige manualmente para cada apertura.
        answer = messagebox.askyesnocancel('Vista de CNShopper',
            '¿Abrir CNShopper en vista de CELULAR?\n\n'
            'Sí = Celular\nNo = Computadora\nCancelar = No abrir')
        if answer is None:
            return None
        mode = 'mobile' if answer else 'desktop'
        client = {}
        if cid is not None:
            with db() as con:
                row = con.execute('SELECT name,email,phone FROM clients WHERE id=?', (cid,)).fetchone()
            if row:
                client = dict(zip(('name', 'email', 'phone'), (v or '' for v in row)))
        def notify_error(error):
            self.after(0, lambda: messagebox.showerror(
                'Navegador independiente',
                'No se pudo abrir Chromium. Comprueba Playwright.\n\n' + error))
        return launch_browser(mode=mode, client=client, on_error=notify_error, attempt_id=attempt_id)

    def begin_registration(self, cid=None):
        cid = cid if cid is not None else self.selected_id
        if cid is None:
            messagebox.showinfo('Selecciona un cliente', 'Selecciona primero una ficha de cliente.')
            return
        with db() as con:
            row = con.execute('SELECT name,email FROM clients WHERE id=?', (cid,)).fetchone()
        if not row or not row[0].strip() or not (row[1] or '').strip():
            messagebox.showwarning('Faltan datos', 'El cliente debe tener nombre y correo guardados.')
            return
        if not messagebox.askyesno('Autorización del cliente',
            f'¿Confirmas que {row[0]} autorizó este registro en CNShopper?\n\n'
            'El titular deberá controlar su correo y proporcionar o confirmar personalmente el OTP. '
            'No se guardarán códigos ni contraseñas.\n\n'
            'Al continuar, autorizas también solicitar automáticamente UN código de verificación '
            'al correo guardado. El titular deberá introducirlo personalmente.'):
            return
        try:
            attempt_id = start_registration(cid)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror('No se pudo iniciar', str(exc))
            return
        self.select(cid)
        self.refresh()
        if self.open_cnshopper(cid, attempt_id=attempt_id) is False:
            messagebox.showwarning('Navegador', 'No se pudo iniciar Chromium. Revisa el mensaje de error o la instalación.')
        self.open_tracking(cid)

    def open_tracking(self, cid=None):
        cid = cid if cid is not None else self.selected_id
        if cid is None:
            messagebox.showinfo('Selecciona un cliente', 'Selecciona una ficha para ver su registro.')
            return
        with db() as con:
            row = con.execute('SELECT name,email,phone FROM clients WHERE id=?', (cid,)).fetchone()
        if not row:
            messagebox.showwarning('Cliente inexistente', 'No se encontró el cliente.')
            return
        win = ctk.CTkToplevel(self)
        win.title(f'Registro asistido — {row[0]}')
        win.geometry('740x590')
        win.configure(fg_color='#101722')
        win.grab_set()
        ctk.CTkLabel(win, text=f'Registro asistido: {row[0]}',
                     font=ctk.CTkFont(size=21, weight='bold')).pack(anchor='w', padx=20, pady=(17, 5))
        ctk.CTkLabel(win, text='Copia los datos al navegador. El cliente controla la verificación OTP.',
                     text_color='#AABBD0').pack(anchor='w', padx=20, pady=(0, 12))
        for label, value in [('Nombre', row[0]), ('Correo', row[1] or ''), ('Teléfono', row[2] or '')]:
            line = ctk.CTkFrame(win, fg_color='#192536')
            line.pack(fill='x', padx=20, pady=3)
            ctk.CTkLabel(line, text=f'{label}: {value}', anchor='w').pack(side='left', padx=12, pady=9)
            ctk.CTkButton(line, text='Copiar', width=80,
                          command=lambda v=value: self.copy_value(v)).pack(side='right', padx=8)
        ctk.CTkButton(win, text='Abrir página de CNShopper',
                      command=lambda: self.open_cnshopper(cid)).pack(anchor='w', padx=20, pady=12)
        state_label = ctk.CTkLabel(win, text='', font=ctk.CTkFont(size=15, weight='bold'))
        state_label.pack(anchor='w', padx=20)
        ctk.CTkLabel(win, text='Observaciones (nunca incluyas códigos OTP ni contraseñas)').pack(anchor='w', padx=20, pady=(12, 3))
        observation = ctk.CTkEntry(win, placeholder_text='Notas del intento')
        observation.pack(fill='x', padx=20)
        buttons = ctk.CTkFrame(win, fg_color='transparent')
        buttons.pack(fill='x', padx=17, pady=10)
        history_frame = ctk.CTkScrollableFrame(win, fg_color='#192536')
        history_frame.pack(fill='both', expand=True, padx=20, pady=(0, 15))

        def redraw():
            attempt = latest_registration(cid)
            state_label.configure(text=f'Estado actual: {attempt[1] if attempt else "No iniciado"}')
            for child in buttons.winfo_children():
                child.destroy()
            for child in history_frame.winfo_children():
                child.destroy()
            if attempt and attempt[1] in ('En proceso', 'Esperando OTP'):
                choices = [('Esperando OTP', 'Esperando OTP'), ('Completado', 'Completado'),
                           ('Cancelado', 'Cancelar registro')]
                for state, label in choices:
                    if state == 'Completado' and attempt[1] != 'Esperando OTP':
                        continue
                    ctk.CTkButton(buttons, text=label, width=145,
                                  command=lambda st=state, aid=attempt[0]: set_state(aid, st)).pack(side='left', padx=3)
            for rid, status, started, finished, notes in registration_history(cid):
                ctk.CTkLabel(history_frame, text=f'Intento #{rid}  •  {status}  •  Inicio: {started}',
                             font=ctk.CTkFont(weight='bold')).pack(anchor='w', padx=8, pady=(9, 1))
                if finished or notes:
                    ctk.CTkLabel(history_frame, text=f'Fin: {finished or "—"}  •  {notes or "Sin observaciones"}',
                                 wraplength=630, justify='left', text_color='#AABBD0').pack(anchor='w', padx=8)
            self.update_tracking_label()

        def set_state(aid, state):
            if state == 'Completado' and not messagebox.askyesno('Confirmar',
                '¿El titular completó su verificación y confirmaste que el registro finalizó?', parent=win):
                return
            if state == 'Cancelado' and not messagebox.askyesno('Cancelar',
                '¿Deseas cancelar este intento?', parent=win):
                return
            try:
                change_registration(aid, state, observation.get())
            except (ValueError, sqlite3.Error) as exc:
                messagebox.showerror('Error', str(exc), parent=win)
                return
            self.refresh()
            redraw()
        redraw()

    def copy_value(self, value):
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update()

    def open_backups(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        os.startfile(BACKUP_DIR)

    def refresh(self):
        for w in self.listbox.winfo_children():
            w.destroy()
        term = self.search.get().strip() if hasattr(self, "search") else ""
        with db() as con:
            rows = con.execute("""SELECT id,name,email,phone,contact,status,notes,created_at
                                  FROM clients
                                  WHERE name LIKE ? OR email LIKE ? OR phone LIKE ? OR contact LIKE ?
                                  ORDER BY id DESC""",
                               tuple([f"%{term}%"] * 4)).fetchall()
            counts = {
                "total": con.execute("SELECT COUNT(*) FROM clients").fetchone()[0],
                "pending": con.execute("SELECT COUNT(*) FROM clients WHERE status='Pendiente'").fetchone()[0],
                "process": con.execute("SELECT COUNT(*) FROM clients WHERE status='En proceso'").fetchone()[0],
                "done": con.execute("SELECT COUNT(*) FROM clients WHERE status='Completado'").fetchone()[0]
            }
        for key, value in counts.items():
            self.stats[key].configure(text=str(value))
        if not rows:
            ctk.CTkLabel(self.listbox, text="No hay clientes que coincidan con la búsqueda.",
                         text_color="#9AABC0").pack(pady=30)
            return
        for cid, name, email, phone, contact, status, notes, created in rows:
            card = ctk.CTkFrame(self.listbox, fg_color="#223248", corner_radius=10)
            card.pack(fill="x", padx=8, pady=6)
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=13, pady=(9, 2))
            ctk.CTkLabel(top, text=name, font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
            ctk.CTkLabel(top, text=status, text_color="#8FC5FF").pack(side="right")
            contact_text = "  •  ".join(x for x in [email, phone] if x) or contact
            ctk.CTkLabel(card, text=contact_text, text_color="#B3C2D4").pack(anchor="w", padx=13)
            ctk.CTkLabel(card, text=f"Agregado: {created}", text_color="#8195AD",
                         font=ctk.CTkFont(size=10)).pack(anchor="w", padx=13, pady=(2, 0))
            if notes:
                ctk.CTkLabel(card, text=notes, text_color="#8FA3BC",
                             wraplength=760, justify="left").pack(anchor="w", padx=13, pady=(3, 0))
            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.pack(fill="x", padx=9, pady=(5, 8))
            ctk.CTkButton(actions, text="Editar", width=80, height=27,
                          command=lambda x=cid: self.select(x)).pack(side="left", padx=3)
            ctk.CTkButton(actions, text="Abrir CNShopper", width=115, height=27,
                          command=lambda x=cid: self.open_cnshopper(x)).pack(side="left", padx=3)
            ctk.CTkButton(actions, text="Iniciar registro", width=115, height=27,
                          fg_color="#286B59", command=lambda x=cid: self.begin_registration(x)).pack(side="left", padx=3)
            ctk.CTkButton(actions, text="Seguimiento", width=100, height=27,
                          fg_color="#40516A", command=lambda x=cid: self.open_tracking(x)).pack(side="left", padx=3)
            ctk.CTkButton(actions, text="Eliminar", width=75, height=27,
                          fg_color="#713B45", hover_color="#914B58",
                          command=lambda x=cid: self.delete(x)).pack(side="right", padx=3)


if __name__ == "__main__":
    app = App()
    app.mainloop()
