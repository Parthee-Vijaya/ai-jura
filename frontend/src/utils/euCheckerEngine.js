/**
 * Small deterministic interpreter for the European Commission checker JSON.
 *
 * The EC graph contains both user-facing questions and invisible "hub" nodes.
 * Hub nodes only inspect flags and route to the next question/result. Keeping
 * that traversal here makes the React page a renderer instead of a second,
 * partial implementation of the decision graph.
 */

export function selectedSet(answer) {
  if (Array.isArray(answer)) return new Set(answer.map(Number));
  if (answer === null || answer === undefined) return new Set();
  return new Set([Number(answer)]);
}

export function evalCondition(condition, answer, flags) {
  if ('answer_is' in condition) {
    return Number(answer) === Number(condition.answer_is);
  }
  if ('flag_equals' in condition) {
    const { flag_name: flagName, value } = condition.flag_equals;
    return flags[flagName] === value;
  }

  const selected = selectedSet(answer);
  if ('if_any_answer_in' in condition) {
    return condition.if_any_answer_in.some((value) => selected.has(Number(value)));
  }
  if ('if_none_selected_in' in condition) {
    return !condition.if_none_selected_in.some((value) => selected.has(Number(value)));
  }
  if ('is_this_exact_match_selected' in condition) {
    const target = new Set(condition.is_this_exact_match_selected.map(Number));
    if (target.size !== selected.size) return false;
    for (const value of target) {
      if (!selected.has(value)) return false;
    }
    return true;
  }

  // Unknown EC condition. Failing closed avoids taking an unintended branch.
  return false;
}

export function evalRouting(node, answer, flags) {
  for (const route of node?.routing || []) {
    const matches = (route.conditions || []).every((condition) =>
      evalCondition(condition, answer, flags),
    );
    if (matches) return route;
  }
  return null;
}

export function applyFlagOps(flags, operations, answer = null) {
  if (!operations) return flags;

  const next = { ...flags };
  for (const operation of operations) {
    const conditions = Array.isArray(operation.condition)
      ? operation.condition
      : operation.condition
        ? [operation.condition]
        : [];
    const matches = conditions.every((condition) =>
      evalCondition(condition, answer, next),
    );
    if (!matches) continue;
    next[operation.flag_name] = operation.value;
  }
  return next;
}

/**
 * Follow invisible EC hub nodes until a visible question or END is reached.
 * A bounded traversal and cycle detection turn corrupt upstream data into a
 * recoverable UI error instead of a blank page.
 */
export function resolveAutomaticNodes({
  qid,
  flags,
  questionsLogic,
  questionsContent,
  maxHops = 25,
}) {
  let currentQid = qid || 'END';
  let nextFlags = { ...flags };
  const visited = new Set();

  for (let hop = 0; hop < maxHops; hop += 1) {
    if (currentQid === 'END' || currentQid === null) {
      return { qid: 'END', flags: nextFlags, error: null };
    }

    const node = questionsLogic[currentQid];
    const content = questionsContent[currentQid];
    if (node && content) {
      return { qid: currentQid, flags: nextFlags, error: null };
    }
    if (!node) {
      return {
        qid: currentQid,
        flags: nextFlags,
        error: `EC-flowet peger på et ukendt trin: ${currentQid}`,
      };
    }
    if (node.type !== 'hub') {
      return {
        qid: currentQid,
        flags: nextFlags,
        error: `EC-trinnet ${currentQid} mangler visningstekst`,
      };
    }
    if (visited.has(currentQid)) {
      return {
        qid: currentQid,
        flags: nextFlags,
        error: `EC-flowet indeholder en løkke ved ${currentQid}`,
      };
    }
    visited.add(currentQid);

    const route = evalRouting(node, null, nextFlags);
    if (!route) {
      return {
        qid: currentQid,
        flags: nextFlags,
        error: `EC-flowet kunne ikke vælge en rute fra ${currentQid}`,
      };
    }
    nextFlags = applyFlagOps(nextFlags, route.set_flags, null);
    currentQid = route.go_to || 'END';
  }

  return {
    qid: currentQid,
    flags: nextFlags,
    error: `EC-flowet overskred ${maxHops} automatiske trin`,
  };
}

/** Remove translation-pipeline markers while retaining their useful fallback. */
export function cleanTranslatedText(value, fallback = '') {
  if (typeof value !== 'string') return fallback;
  const cleaned = value
    .replace(/^\s*\[Kontekst:[^\]]+\]\s*/i, '')
    .trim();
  return cleaned || fallback;
}

/**
 * EC's flags_content values are usually plain strings, but some cache
 * versions contain richer objects. Normalize both forms without spreading a
 * string into numeric object keys. Flags without public copy remain available
 * as technical trace data, but are not presented as user-facing conclusions.
 */
export function normalizeRaisedFlags(flags, flagsContent = {}) {
  return Object.entries(flags || {})
    .filter(([, value]) => value !== false && value !== undefined && value !== null)
    .map(([name, value]) => {
      const meta = flagsContent[name];
      if (typeof meta === 'string') {
        return {
          name,
          value,
          description: cleanTranslatedText(meta),
          hasPublicCopy: Boolean(cleanTranslatedText(meta)),
        };
      }
      if (meta && typeof meta === 'object') {
        const label = cleanTranslatedText(meta.label || meta.title);
        const description = cleanTranslatedText(meta.description || meta.text);
        return {
          name,
          value,
          ...meta,
          label,
          description,
          hasPublicCopy: Boolean(label || description),
        };
      }
      return { name, value, hasPublicCopy: false };
    });
}
