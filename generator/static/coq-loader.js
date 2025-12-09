/**
 * Coq Source Loader
 * Fetches Coq source code from GitHub and extracts/highlights specific lemmas.
 */

/**
 * Load and display a lemma's source code from GitHub.
 * @param {string} githubRawBase - Base URL for GitHub raw content
 * @param {string} filePath - Path to the .v file relative to repo root
 * @param {string} lemmaName - Name of the lemma to extract
 */
async function loadLemmaSource(githubRawBase, filePath, lemmaName) {
    const container = document.getElementById('coq-source');
    
    try {
        const url = `${githubRawBase}/${filePath}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch: ${response.status} ${response.statusText}`);
        }
        
        const code = await response.text();
        const extracted = extractLemma(code, lemmaName);
        
        if (extracted) {
            container.innerHTML = highlightCoq(extracted);
        } else {
            container.innerHTML = `<span class="error">Could not find lemma "${lemmaName}" in source file.</span>`;
        }
    } catch (error) {
        console.error('Error loading Coq source:', error);
        container.innerHTML = `<span class="error">Error loading source: ${error.message}</span>\n\n` +
            `<span class="coq-comment">(* The source will be available once the repository is public *)</span>`;
    }
}

/**
 * Extract a specific lemma/theorem from Coq source code.
 * @param {string} code - Full Coq source code
 * @param {string} lemmaName - Name of the lemma to extract
 * @returns {string|null} - Extracted lemma code or null if not found
 */
function extractLemma(code, lemmaName) {
    const lines = code.split('\n');
    
    // Pattern to match lemma/theorem declaration
    const declPattern = new RegExp(
        `^\\s*(Lemma|Theorem|Corollary|Proposition|Fact|Remark)\\s+${escapeRegex(lemmaName)}\\b`,
        'i'
    );
    
    let startLine = -1;
    let endLine = -1;
    let depth = 0;
    let inProof = false;
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();
        
        // Remove comments for pattern matching
        const lineNoComment = trimmed.replace(/\(\*.*?\*\)/g, '');
        
        if (startLine === -1) {
            // Look for the lemma declaration
            if (declPattern.test(line)) {
                startLine = i;
                // Also capture preceding comment if present
                let commentStart = i;
                for (let j = i - 1; j >= 0; j--) {
                    const prevLine = lines[j].trim();
                    if (prevLine === '') {
                        continue;
                    }
                    if (prevLine.endsWith('*)')) {
                        // Found end of comment, look for start
                        for (let k = j; k >= 0; k--) {
                            if (lines[k].trim().startsWith('(*')) {
                                commentStart = k;
                                break;
                            }
                        }
                        break;
                    }
                    break;
                }
                startLine = commentStart;
            }
        } else {
            // Look for the end of the lemma (Qed, Defined, or Admitted)
            if (/\b(Qed|Defined|Admitted)\s*\./.test(lineNoComment)) {
                endLine = i;
                break;
            }
        }
    }
    
    if (startLine !== -1 && endLine !== -1) {
        return lines.slice(startLine, endLine + 1).join('\n');
    } else if (startLine !== -1) {
        // Lemma found but no end marker - take next 50 lines as fallback
        return lines.slice(startLine, Math.min(startLine + 50, lines.length)).join('\n') + 
            '\n(* ... truncated ... *)';
    }
    
    return null;
}

/**
 * Apply syntax highlighting to Coq code.
 * @param {string} code - Coq source code
 * @returns {string} - HTML with syntax highlighting
 */
function highlightCoq(code) {
    // Escape HTML first
    let html = escapeHtml(code);
    
    // Keywords
    const keywords = [
        'Lemma', 'Theorem', 'Corollary', 'Proposition', 'Fact', 'Remark',
        'Definition', 'Fixpoint', 'CoFixpoint', 'Inductive', 'CoInductive',
        'Record', 'Structure', 'Class', 'Instance', 'Section', 'End',
        'Variable', 'Variables', 'Context', 'Hypothesis', 'Hypotheses',
        'Let', 'Proof', 'Qed', 'Defined', 'Admitted', 'Abort',
        'Require', 'Import', 'Export', 'Open', 'Scope', 'Local', 'Global',
        'Set', 'Unset', 'From', 'Module', 'Type', 'Prop', 'Set',
        'forall', 'exists', 'fun', 'match', 'with', 'end', 'if', 'then', 'else',
        'as', 'in', 'return', 'where', 'fix', 'cofix', 'struct',
        'Arguments', 'Implicit', 'Notation', 'Infix', 'Reserved',
        'Canonical', 'Coercion', 'Hint', 'Resolve', 'Rewrite', 'Unfold'
    ];
    
    // Tactics
    const tactics = [
        'intros', 'intro', 'apply', 'exact', 'refine', 'assumption',
        'rewrite', 'replace', 'subst', 'simpl', 'unfold', 'fold',
        'destruct', 'induction', 'case', 'elim', 'inversion', 'injection',
        'split', 'left', 'right', 'exists', 'constructor', 'econstructor',
        'reflexivity', 'symmetry', 'transitivity', 'congruence', 'ring', 'field', 'lia', 'lra',
        'auto', 'eauto', 'trivial', 'easy', 'tauto', 'intuition',
        'assert', 'pose', 'set', 'remember', 'generalize', 'specialize',
        'clear', 'rename', 'move', 'have', 'suff', 'wlog',
        'repeat', 'try', 'do', 'progress', 'first', 'solve',
        'by', 'done', 'now', 'congr', 'under', 'over'
    ];
    
    // Highlight comments (* ... *)
    html = html.replace(/\(\*[\s\S]*?\*\)/g, '<span class="coq-comment">$&</span>');
    
    // Highlight strings "..."
    html = html.replace(/"[^"]*"/g, '<span class="coq-string">$&</span>');
    
    // Highlight keywords (word boundaries)
    keywords.forEach(kw => {
        const regex = new RegExp(`\\b(${kw})\\b`, 'g');
        html = html.replace(regex, '<span class="coq-keyword">$1</span>');
    });
    
    // Highlight tactics
    tactics.forEach(tac => {
        const regex = new RegExp(`\\b(${tac})\\b`, 'g');
        html = html.replace(regex, '<span class="coq-tactic">$1</span>');
    });
    
    return html;
}

/**
 * Escape special regex characters in a string.
 */
function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Escape HTML special characters.
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

