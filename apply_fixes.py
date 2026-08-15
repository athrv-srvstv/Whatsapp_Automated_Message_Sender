#!/usr/bin/env python3
"""
apply_fixes.py
--------------
Applies seven fixes to the automated-whatsapp-interview-messenger repo.
Every fix is an exact-match string replacement, so if the repo has moved on
the script refuses to guess - it tells you which fix no longer matches.

    python3 apply_fixes.py --repo . --dry-run   # show what would change
    python3 apply_fixes.py --repo .             # apply, keeping .bak backups

Originals are saved as main.py.bak / alright/__init__.py.bak.
"""

import argparse
import shutil
import sys
from pathlib import Path

FIXES = {}


def fix(filename, name, why):
    def register(pair):
        FIXES.setdefault(filename, []).append((name, why, pair[0], pair[1]))
        return pair
    return register


# ---------------------------------------------------------------- main.py

fix("main.py", "1. capacity arithmetic",
    "available_time added a phantom 60 minutes, so head() selected 84 people for a "
    "3h evening that only fits 63. The extra 21 were picked but never messaged.")((
    '''    available_time = abs(int(minutes)) + 60''',
    '''    available_time = abs(int(minutes))''',
))

fix("main.py", "2. slot burning on failed sends",
    "batch_count advanced every time i %% at_once == 0. Because i only increments on "
    "SUCCESS, each failed send at a batch boundary consumed a whole 20-minute slot. "
    "Three dead numbers in a row silently destroyed 18:00, 18:20 and 18:40. "
    "The batch index is now derived from i, so failures cost nothing.")((
    '''    if i%PARAMS["at_once"] == 0:
       interview_time = calculate_time(batch_count, PARAMS["start_time"], PARAMS["end_time"], PARAMS["duration"])
       batch_count += 1
''',
    '''    # Derive the batch index from the number of SUCCESSFUL sends so far.
    # A failed send must not advance the clock.
    batch_count = i // PARAMS["at_once"]
    interview_time = calculate_time(batch_count, PARAMS["start_time"], PARAMS["end_time"], PARAMS["duration"])
''',
))

fix("main.py", "3. header cache never updated",
    "After adding the Notified_ column, `headers` was not updated, so every "
    "subsequent message re-wrote the header cell. One wasted Sheets write per "
    "person - 580 wasted API calls, against a 60/min quota.")((
    '''        sheet.update_cell(1, new_col_index, update_column)
        update_col_index = new_col_index
        print(f"Added new column '{update_column}' at position {new_col_index}")''',
    '''        sheet.update_cell(1, new_col_index, update_column)
        update_col_index = new_col_index
        headers.append(update_column)  # keep the cache in sync, don't rewrite it 580 times
        print(f"Added new column '{update_column}' at position {new_col_index}")''',
))

fix("main.py", "4. phone numbers that are blank or 'same'",
    "format_phone_number('same') with no backup returned the literal string '+91'. "
    "Anything with under 10 digits now returns None and the person is skipped and "
    "logged instead of being messaged at a garbage number.")((
    '''    # Extract only digits from the input string
    digits = re.findall(r'\\d+', phone_number)
    digits_only = ''.join(digits)
    ''',
    '''    # Extract only digits from the input string
    digits = re.findall(r'\\d+', phone_number)
    digits_only = ''.join(digits)

    # Too few digits to be a real number - caller must skip this person
    if len(digits_only) < 10:
        return None
    ''',
))

fix("main.py", "5. subsystem matching was exact-equality",
    "validate_subsystem_field required the sheet value to equal target_subsystem "
    "character for character. A form option written 'Artificial Intelligence (AI)' "
    "silently matched nobody. Now compares on alphanumerics and allows the target "
    "to appear inside the answer.")((
    '''    def validate_subsystem_field(string):
        return string.lower().strip() == PARAMS["target_subsystem"].lower().strip()''',
    '''    def validate_subsystem_field(string):
        # tolerate punctuation, casing and suffixes like "(AI)" or " - Software"
        answer = re.sub(r'[^a-z0-9]+', ' ', str(string).lower()).strip()
        target = re.sub(r'[^a-z0-9]+', ' ', str(PARAMS["target_subsystem"]).lower()).strip()
        if not target:
            return True
        return answer == target or target in answer''',
))

fix("main.py", "6. treat a fast failure as a failure",
    "run_with_timeout only detected timeouts. Now send_direct_message returns "
    "True/False, so an invalid number is caught in ~3 seconds instead of burning "
    "the full timeout. At 580 people that is a lot of dead waiting.")((
    '''            result, status = run_with_timeout(messenger.send_direct_message, args=(str(phone_number),message,False), timeout=PARAMS["timeout"])
            if status == False:''',
    '''            result, status = run_with_timeout(messenger.send_direct_message, args=(str(phone_number),message,False), timeout=PARAMS["timeout"])
            if status == True and result == False:
                # the chat box never appeared - almost always not a WhatsApp number
                print("Number appears invalid (no chat box).")
                if phone_number_backup:
                    print(f"Attempting with backup phone number ({phone_number_backup})")
                    return send_message(name, phone_number_backup, message)
                return False
            if status == False:''',
))

fix("main.py", "7. skip people with no usable number",
    "Adds an explicit skip so a None from format_phone_number cannot reach WhatsApp.")((
    '''    print(f"Attempting to schedule: Interview {i+1}/{len(new_rows)} (Row ID {row['id']}) @ {interview_time} for {subsystem} [{name}({phone_number})]")''',
    '''    if phone_number in (None, "", "+91"):
        print(f"SKIPPED (no usable phone number): {name} (Row ID {row['id']})")
        update_sheet_values("Notified_"+PARAMS["target_subsystem"], [row["id"]], ["No valid number"])
        continue

    print(f"Attempting to schedule: Interview {i+1}/{len(new_rows)} (Row ID {row['id']}) @ {interview_time} for {subsystem} [{name}({phone_number})]")''',
))


# ------------------------------------------------------- alright/__init__.py

fix("alright/__init__.py", "8. brittle absolute XPath",
    "The message box was located by a full path from <body>. WhatsApp Web has "
    "reshuffled its DOM many times since this was written, and that path is the "
    "single most likely thing to be broken today. Now tries several resilient "
    "selectors, detects the 'invalid number' dialog, and returns True/False.")((
    '''        try:
            inp_xpath = (
                '/html/body/div[1]/div/div[1]/div[3]/div/div[4]/div/footer/div[1]/div/span/div/div[2]/div/div[3]/div'
            )
            # inp_xpath = '//*[@id="main"]/footer/div/div/span[2]/div/div[2]/div/div/div'
            input_box = self.wait.until(
                EC.presence_of_element_located((By.XPATH, inp_xpath))
            )
            for line in message.split("\\n"):
                input_box.send_keys(line)
                ActionChains(self.browser).key_down(Keys.SHIFT).key_down(
                    Keys.ENTER
                ).key_up(Keys.ENTER).key_up(Keys.SHIFT).perform()
            if timeout:
                time.sleep(timeout)
            input_box.send_keys(Keys.ENTER)
            LOGGER.info(f"Message sent successfuly to {self.mobile}")
        except (NoSuchElementException, Exception) as bug:
            LOGGER.exception(f"Failed to send a message to {self.mobile} - {bug}")
            LOGGER.info("send_message() finished running!")''',
    '''        # Ordered most-specific first. WhatsApp Web changes its DOM often, so we try
        # several rather than trusting one absolute path.
        BOX_SELECTORS = [
            '//div[@id="main"]//footer//div[@contenteditable="true"]',
            '//footer//div[@contenteditable="true"]',
            '//div[@contenteditable="true"][@data-tab="10"]',
            '//div[@contenteditable="true"][@role="textbox"]',
        ]
        # "Phone number shared via url is invalid" / "isn't on WhatsApp"
        INVALID_POPUP = '//div[@role="dialog"] | //div[@data-animate-modal-body="true"]'

        input_box = None
        deadline = time.time() + 25
        while time.time() < deadline and input_box is None:
            for selector in BOX_SELECTORS:
                found = self.browser.find_elements(By.XPATH, selector)
                if found and found[0].is_displayed():
                    input_box = found[0]
                    break
            if input_box:
                break
            if self.browser.find_elements(By.XPATH, INVALID_POPUP):
                LOGGER.info(f"{self.mobile} is not a valid WhatsApp number")
                return False
            time.sleep(0.5)

        if input_box is None:
            LOGGER.info(f"Could not find the message box for {self.mobile}. "
                        f"If this happens for everyone, WhatsApp Web changed its "
                        f"layout - update BOX_SELECTORS.")
            return False

        try:
            input_box.click()
            lines = message.split("\\n")
            for index, line in enumerate(lines):
                input_box.send_keys(line)
                if index < len(lines) - 1:   # no trailing blank line
                    ActionChains(self.browser).key_down(Keys.SHIFT).key_down(
                        Keys.ENTER
                    ).key_up(Keys.ENTER).key_up(Keys.SHIFT).perform()
            if timeout:
                time.sleep(timeout)
            input_box.send_keys(Keys.ENTER)
            LOGGER.info(f"Message sent successfully to {self.mobile}")
            return True
        except (NoSuchElementException, Exception) as bug:
            LOGGER.exception(f"Failed to send a message to {self.mobile} - {bug}")
            return False''',
))

fix("alright/__init__.py", "9. propagate the send result",
    "send_direct_message swallowed send_message's outcome, so main.py could not "
    "tell a delivered message from a silent failure.")((
    '''    def send_direct_message(self, mobile: str, message: str, saved: bool = True):
        if saved:
            self.find_by_username(mobile)
        else:
            self.find_user(mobile)
        self.send_message(message)''',
    '''    def send_direct_message(self, mobile: str, message: str, saved: bool = True):
        if saved:
            self.find_by_username(mobile)
        else:
            self.find_user(mobile)
        return self.send_message(message)''',
))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="path to the repo root")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    if not (root / "main.py").exists():
        sys.exit(f"No main.py in {root} - point --repo at the repo root.")

    total = failed = 0
    for filename, patches in FIXES.items():
        path = root / filename
        if not path.exists():
            print(f"!! {filename} not found, skipping {len(patches)} fix(es)")
            failed += len(patches)
            continue

        text = original = path.read_text(encoding="utf-8")
        print(f"\n{filename}")
        print("=" * 70)
        for name, why, old, new in patches:
            count = text.count(old)
            if count == 1:
                text = text.replace(old, new)
                print(f"  [ok]   {name}")
                total += 1
            elif count == 0:
                print(f"  [MISS] {name}  - pattern not found, apply by hand")
                failed += 1
            else:
                print(f"  [MISS] {name}  - matched {count} times, too risky")
                failed += 1
            for line in why.split(". "):
                if line.strip():
                    print(f"         {line.strip().rstrip('.')}.")

        if text != original and not args.dry_run:
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
            path.write_text(text, encoding="utf-8")
            print(f"  -> written (backup at {path.name}.bak)")

    print(f"\n{'DRY RUN - nothing written. ' if args.dry_run else ''}"
          f"{total} applied, {failed} need manual attention.")


if __name__ == "__main__":
    main()
