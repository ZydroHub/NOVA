import React, { useState, useCallback } from 'react';

const ROW_NUM = '1234567890'.split('');
const ROW1 = 'QWERTYUIOP'.split('');
const ROW2 = 'ASDFGHJKL'.split('');
const ROW3 = 'ZXCVBNM'.split('');

// Large touch targets for 480×800 / 4.3" screen — keys fill width and are easy to tap
const KEY_STYLE =
    'flex-1 min-w-0 h-14 px-1 flex items-center justify-center font-["VT323"] text-2xl border-2 border-[var(--pixel-border)] bg-[var(--pixel-surface)] text-[var(--pixel-text)] active:translate-y-0.5 active:shadow-none shadow-[2px_2px_0_0_var(--pixel-border)] transition-all select-none touch-manipulation';

const KEY_SPECIAL =
    'flex-[1.2] min-w-0 h-14 px-2 flex items-center justify-center font-["Press_Start_2P"] text-xs border-2 border-[var(--pixel-border)] bg-[var(--pixel-surface)] text-[var(--pixel-text)] active:translate-y-0.5 active:shadow-none shadow-[2px_2px_0_0_var(--pixel-border)] transition-all select-none touch-manipulation';

const KEY_ACCENT =
    'h-14 px-2 flex items-center justify-center font-["Press_Start_2P"] text-xs border-2 border-[var(--pixel-primary)] bg-[var(--pixel-primary)] text-black active:translate-y-0.5 active:shadow-none shadow-[2px_2px_0_0_var(--pixel-border)] transition-all select-none touch-manipulation';

const KEY_SPACE = 'flex-[3] min-w-0 ' + KEY_ACCENT;
const KEY_ENTER = 'flex-1 min-w-[72px] ' + KEY_ACCENT;

// Only text-like inputs support setSelectionRange; number/date/time etc. do not
const SELECTION_TYPES = new Set(['text', 'search', 'url', 'tel', 'password']);
function supportsSelection(el) {
    if (!el) return false;
    if (el.tagName === 'TEXTAREA') return true;
    if (el.tagName !== 'INPUT') return false;
    return SELECTION_TYPES.has((el.type || 'text').toLowerCase());
}

function insertAtCursor(el, text) {
    if (!el || typeof el.value === 'undefined') return;
    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? start;
    const before = el.value.slice(0, start);
    const after = el.value.slice(end);
    const newValue = before + text + after;
    el.value = newValue;
    if (supportsSelection(el)) {
        const newPos = start + text.length;
        el.setSelectionRange(newPos, newPos);
    }
    el.dispatchEvent(new Event('input', { bubbles: true }));
}

function backspace(el) {
    if (!el || typeof el.value === 'undefined') return;
    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? start;
    if (start === 0 && end === 0) return;
    const delStart = start === end ? start - 1 : start;
    const delEnd = end;
    const before = el.value.slice(0, delStart);
    const after = el.value.slice(delEnd);
    el.value = before + after;
    if (supportsSelection(el)) {
        el.setSelectionRange(delStart, delStart);
    }
    el.dispatchEvent(new Event('input', { bubbles: true }));
}

function keyEnter(el) {
    if (!el) return;
    // Dispatch Enter keydown so the target's onKeyDown runs (e.g. chat sends message, other fields get newline)
    el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', shiftKey: false, bubbles: true }));
}

function syncStateAfterChange(el, syncRef) {
    if (el && typeof el.value !== 'undefined' && syncRef?.current) {
        syncRef.current(el.value);
    }
}

export default function VirtualKeyboard({ visible, mode = 'inline', focusedElementRef = null, syncInputValueRef = null }) {
    const [shift, setShift] = useState(false);

    // Prefer ref from context so we still type into the input after key taps (which move focus to the button)
    const getTarget = useCallback(() => {
        if (focusedElementRef?.current) return focusedElementRef.current;
        const el = document.activeElement;
        if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) return el;
        return null;
    }, [focusedElementRef]);

    const handleKey = useCallback(
        (char) => (e) => {
            e.preventDefault();
            const el = getTarget();
            if (!el) return;
            insertAtCursor(el, shift ? char : char.toLowerCase());
            syncStateAfterChange(el, syncInputValueRef);
            setShift(false);
        },
        [getTarget, shift, syncInputValueRef]
    );

    const handleNumberKey = useCallback(
        (char) => (e) => {
            e.preventDefault();
            const el = getTarget();
            if (!el) return;
            insertAtCursor(el, char);
            syncStateAfterChange(el, syncInputValueRef);
        },
        [getTarget, syncInputValueRef]
    );

    const handleBackspace = useCallback(
        (e) => {
            e.preventDefault();
            const el = getTarget();
            backspace(el);
            syncStateAfterChange(el, syncInputValueRef);
        },
        [getTarget, syncInputValueRef]
    );

    const handleSpace = useCallback(
        (e) => {
            e.preventDefault();
            const el = getTarget();
            insertAtCursor(el, ' ');
            syncStateAfterChange(el, syncInputValueRef);
        },
        [getTarget, syncInputValueRef]
    );

    const handleEnter = useCallback(
        (e) => {
            e.preventDefault();
            keyEnter(getTarget());
        },
        [getTarget]
    );

    const handleShift = useCallback((e) => {
        e.preventDefault();
        setShift((s) => !s);
    }, []);

    if (!visible) {
        if (mode === 'inline') return <div className="h-0 overflow-hidden" aria-hidden />;
        return null;
    }

    const containerClass =
        mode === 'overlay'
            ? 'fixed bottom-0 left-0 right-0 z-50 border-t-4 border-[var(--pixel-border)] bg-[var(--pixel-surface)] p-2 pb-[max(12px,env(safe-area-inset-bottom))] shadow-[0_-4px_0_0_var(--pixel-border)]'
            : 'flex-shrink-0 border-t-4 border-[var(--pixel-border)] bg-[var(--pixel-surface)] p-2 pb-[max(8px,env(safe-area-inset-bottom))]';

    return (
        <div
            className={containerClass}
            role="group"
            aria-label="On-screen keyboard"
            data-virtual-keyboard
        >
            <div className="w-full max-w-[100%] px-2 flex flex-col gap-2">
                <div className="flex w-full gap-1">
                    {ROW_NUM.map((char) => (
                        <button
                            key={char}
                            type="button"
                            className={KEY_STYLE}
                            onMouseDown={(e) => {
                                e.preventDefault();
                                handleNumberKey(char)(e);
                            }}
                            onTouchEnd={(e) => {
                                e.preventDefault();
                                handleNumberKey(char)(e);
                            }}
                        >
                            {char}
                        </button>
                    ))}
                </div>
                <div className="flex w-full gap-1">
                    {(shift ? ROW1 : ROW1.map((c) => c.toLowerCase())).map((char) => (
                        <button
                            key={char}
                            type="button"
                            className={KEY_STYLE}
                            onMouseDown={(e) => {
                                e.preventDefault();
                                handleKey(char)(e);
                            }}
                            onTouchEnd={(e) => {
                                e.preventDefault();
                                handleKey(char)(e);
                            }}
                        >
                            {char}
                        </button>
                    ))}
                </div>
                <div className="flex w-full gap-1">
                    {(shift ? ROW2 : ROW2.map((c) => c.toLowerCase())).map((char) => (
                        <button
                            key={char}
                            type="button"
                            className={KEY_STYLE}
                            onMouseDown={(e) => handleKey(char)(e)}
                            onTouchEnd={(e) => {
                                e.preventDefault();
                                handleKey(char)(e);
                            }}
                        >
                            {char}
                        </button>
                    ))}
                </div>
                <div className="flex w-full gap-1">
                    <button
                        type="button"
                        className={KEY_SPECIAL}
                        onMouseDown={handleShift}
                        onTouchEnd={(e) => {
                            e.preventDefault();
                            handleShift(e);
                        }}
                    >
                        {shift ? 'CAPS' : 'shift'}
                    </button>
                    {(shift ? ROW3 : ROW3.map((c) => c.toLowerCase())).map((char) => (
                        <button
                            key={char}
                            type="button"
                            className={KEY_STYLE}
                            onMouseDown={(e) => handleKey(char)(e)}
                            onTouchEnd={(e) => {
                                e.preventDefault();
                                handleKey(char)(e);
                            }}
                        >
                            {char}
                        </button>
                    ))}
                    <button
                        type="button"
                        className={KEY_SPECIAL}
                        onMouseDown={handleBackspace}
                        onTouchEnd={(e) => {
                            e.preventDefault();
                            handleBackspace(e);
                        }}
                    >
                        ⌫
                    </button>
                </div>
                <div className="flex w-full gap-2">
                    <button
                        type="button"
                        className={KEY_SPACE}
                        onMouseDown={handleSpace}
                        onTouchEnd={(e) => {
                            e.preventDefault();
                            handleSpace(e);
                        }}
                    >
                        SPACE
                    </button>
                    <button
                        type="button"
                        className={KEY_ENTER}
                        onMouseDown={handleEnter}
                        onTouchEnd={(e) => {
                            e.preventDefault();
                            handleEnter(e);
                        }}
                    >
                        ENTER
                    </button>
                </div>
            </div>
        </div>
    );
}
