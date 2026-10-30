"""Navegación asistida. El OTP nunca se lee ni se introduce automáticamente."""
import sys
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def diagnostic(message):
    # No registrar datos personales, URLs con tokens, cookies ni OTP.
    print('[CNShopper] ' + message, flush=True)


def fill_if_unique(page, selectors, value):
    """Compatibilidad con las utilidades y pruebas de V4.3."""
    if not value:
        return False
    for selector in selectors:
        try:
            matches = page.locator(selector)
            if matches.count() != 1:
                continue
            field = matches.first
            if field.is_visible() and field.is_enabled() and not field.input_value().strip():
                field.fill(value, timeout=2500)
                return True
        except Exception:
            continue
    return False


def click_visible_unique(page, selectors):
    """Selecciona un único control visible, sin pulsar botones de envío."""
    for selector in selectors:
        try:
            matches = page.locator(selector)
            visible = [matches.nth(i) for i in range(min(matches.count(), 15))
                       if matches.nth(i).is_visible()]
            if len(visible) == 1 and visible[0].is_enabled():
                visible[0].click(timeout=5000)
                return True
        except Exception:
            continue
    return False


def find_email_field(page):
    """Buscar el campo por atributos accesibles sin depender del scroll."""
    if '/register' not in page.url.lower():
        return None
    selectors = [
        'input[placeholder="Email Address"]',
        'input[placeholder*="email" i]',
        'input[type="email"]',
        'input[autocomplete="email"]',
    ]
    for selector in selectors:
        try:
            fields = page.locator(selector)
            candidates = []
            for i in range(min(fields.count(), 12)):
                field = fields.nth(i)
                if field.is_visible() and field.is_enabled():
                    candidates.append(field)
            if len(candidates) == 1:
                return candidates[0]
        except Exception:
            continue
    return None


def registration_email_field(page):
    return find_email_field(page) is not None


def navigate_to_registration(page, mode):
    if mode == 'mobile':
        if not click_visible_unique(page, [
            'nav a:has-text("Me")', 'a:has-text("Me")', 'text="Me"'
        ]):
            diagnostic('No se encontró el botón Me; navegación manual disponible.')
            return False
        try:
            page.wait_for_url('**/member-center/**', timeout=12000)
        except PlaywrightTimeout:
            pass
        if not click_visible_unique(page, [
            'a:has-text("Sign Up")', 'button:has-text("Sign Up")', 'text="Sign Up"'
        ]):
            diagnostic('No se encontró Sign Up; navegación manual disponible.')
            return False
    else:
        if not click_visible_unique(page, [
            'a:has-text("Register")', 'button:has-text("Register")', 'text="Register"'
        ]):
            diagnostic('No se encontró Register; navegación manual disponible.')
            return False
    try:
        page.wait_for_url('**/register**', timeout=15000)
        diagnostic('Página de registro abierta.')
        return True
    except PlaywrightTimeout:
        diagnostic('No se confirmó la página de registro.')
        return False


def assist_form(page, name, email, phone):
    """Rellena solamente el email. No sobrescribe ni envía información."""
    if not email or '/register' not in page.url.lower():
        return False
    field = find_email_field(page)
    if field is None:
        return False
    try:
        # fill funciona también cuando el campo está fuera de la pantalla.
        # Playwright se desplaza al elemento durante la acción.
        current = field.input_value(timeout=3000).strip()
        if current and current != email:
            diagnostic('El campo ya contiene otro correo; no se sobrescribe.')
            return False
        if not current:
            field.fill(email, timeout=8000)
        if field.input_value(timeout=3000).strip() == email:
            try:
                field.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass
            diagnostic('Correo rellenado. Revisar manualmente antes de continuar.')
            return True
    except Exception as exc:
        diagnostic('No se pudo completar el campo: ' + type(exc).__name__)
    return False


def send_verification_once(page, email):
    """Solicita un único OTP tras autorización previa y correo verificado."""
    if '/register' not in page.url.lower():
        return False
    field = find_email_field(page)
    if field is None:
        return False
    try:
        if field.input_value(timeout=2500).strip() != email:
            diagnostic('Correo distinto al autorizado: no se solicita OTP.')
            return False
        controls = page.get_by_role('button', name='Send Verification Code', exact=True)
        if controls.count() != 1 or not controls.first.is_visible() or not controls.first.is_enabled():
            diagnostic('No se encontró un botón único para solicitar el código.')
            return False
        controls.first.click(timeout=6000)
        diagnostic('Solicitud de código pulsada una vez. El titular debe verificar el OTP.')
        return True
    except Exception as exc:
        diagnostic('No se pudo solicitar el código: ' + type(exc).__name__)
        return False



def dismiss_emailnator_cookie_notice(tab):
    """Cierra solo el aviso visible 'Got it'; nunca pulsa otros controles."""
    for _ in range(5):
        try:
            # El aviso puede aparecer después de DOMContentLoaded.
            buttons = tab.get_by_role('button', name='Got it', exact=True)
            if buttons.count() == 1 and buttons.first.is_visible():
                buttons.first.click(timeout=3500)
                diagnostic('Emailnator: aviso de cookies cerrado.')
                return True
            text_button = tab.get_by_text('Got it', exact=True)
            if text_button.count() == 1 and text_button.first.is_visible():
                text_button.first.click(timeout=3500)
                diagnostic('Emailnator: aviso de cookies cerrado.')
                return True
        except Exception as exc:
            diagnostic('Emailnator: aviso de cookies no cerrado: ' + type(exc).__name__)
        tab.wait_for_timeout(500)
    diagnostic('Emailnator: no se encontró aviso de cookies visible; continuando.')
    return False


def open_emailnator_for_manual_review(context, email):
    """Prepara Custom email para consulta manual; nunca lee mensajes ni OTP."""
    tab = context.new_page()
    try:
        tab.goto('https://www.emailnator.com/', wait_until='domcontentloaded', timeout=30000)
        dismiss_emailnator_cookie_notice(tab)

        # En móvil el enlace está debajo de Generate New. Nunca pulsar este último.
        custom = tab.get_by_text('Custom email', exact=True)
        opened = False
        for _ in range(10):
            try:
                if custom.count() == 1 and custom.first.is_visible():
                    custom.first.scroll_into_view_if_needed(timeout=3000)
                    # Puede mostrarse un aviso tardío durante el desplazamiento.
                    dismiss_emailnator_cookie_notice(tab)
                    custom.first.click(timeout=4000)
                    opened = True
                    break
            except Exception as exc:
                diagnostic('Emailnator: reintentando enlace Custom email: ' + type(exc).__name__)
            tab.wait_for_timeout(600)
        if not opened:
            diagnostic('Emailnator: no se pudo pulsar el enlace Custom email; continuar manualmente.')
            return tab

        field = tab.get_by_placeholder('Paste your custom email', exact=False)
        try:
            field.wait_for(state='visible', timeout=8000)
            if field.count() != 1:
                diagnostic('Emailnator: varios campos Custom email; continuar manualmente.')
                return tab
            field.scroll_into_view_if_needed(timeout=3000)
            if field.is_enabled() and not field.input_value().strip():
                field.fill(email, timeout=3500)
                diagnostic('Emailnator: Custom email preparado. GO! y OTP son manuales.')
            else:
                diagnostic('Emailnator: revisar el campo Custom email manualmente.')
        except Exception as exc:
            diagnostic('Emailnator: no apareció el campo Custom email: ' + type(exc).__name__)
        return tab
    except Exception as exc:
        diagnostic('Emailnator: error al abrir la página: ' + type(exc).__name__)
        return tab


def main():
    mode, url, name, email, phone = sys.argv[1:6]
    attempt_id = int(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6].isdigit() else None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        try:
            options = {'accept_downloads': False, 'service_workers': 'block'}
            if mode == 'mobile':
                options.update(playwright.devices['iPhone 13'])
            else:
                options['viewport'] = {'width': 1280, 'height': 850}
            context = browser.new_context(**options)
            try:
                page = context.new_page()
                page.goto(url, wait_until='domcontentloaded', timeout=45000)
                navigate_to_registration(page, mode)
                # También funciona si la persona llega manualmente al formulario.
                # No reintentar después de un autocompletado exitoso.
                filled = False
                requested = False
                emailnator_opened = False
                last_report = 0
                while browser.is_connected() and context.pages:
                    try:
                        current_page = context.pages[0]
                        if not filled and '/register' in current_page.url.lower():
                            filled = assist_form(current_page, name, email, phone)
                            if not filled and time.monotonic() - last_report > 12:
                                diagnostic('Esperando un campo de correo visible y único; puede desplazarse manualmente.')
                                last_report = time.monotonic()
                        if filled and not requested and attempt_id is not None:
                            # No repetir clics aunque el servidor tarde en responder.
                            requested = True
                            if send_verification_once(current_page, email):
                                try:
                                    from database import change_registration
                                    change_registration(attempt_id, 'Esperando OTP',
                                                        'Solicitud de código iniciada; OTP manual')
                                except Exception as exc:
                                    diagnostic('No se pudo actualizar el estado: ' + type(exc).__name__)
                                if not emailnator_opened:
                                    emailnator_opened = True
                                    open_emailnator_for_manual_review(context, email)
                        current_page.wait_for_timeout(1200)
                    except Exception:
                        break
            finally:
                context.close()
        finally:
            browser.close()


if __name__ == '__main__':
    main()
