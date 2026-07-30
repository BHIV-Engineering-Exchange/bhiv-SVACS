// =====================================================
// SAFE NUMBER FORMAT
// =====================================================

export const fmtNum = (
  n?: number | null
) => {

  try {

    if (
      n === undefined ||
      n === null ||
      Number.isNaN(n)
    ) {
      return "0";
    }

    return Number(n).toLocaleString("en-US");

  } catch (error) {

    console.error("fmtNum ERROR:", error);

    return "0";
  }
};

// =====================================================
// SAFE PERCENT FORMAT
// =====================================================

export const fmtPct = (
  v?: number | null,
  digits = 1
) => {

  try {

    if (
      v === undefined ||
      v === null ||
      Number.isNaN(v)
    ) {
      return "0%";
    }

    return `${(Number(v) * 100).toFixed(digits)}%`;

  } catch (error) {

    console.error("fmtPct ERROR:", error);

    return "0%";
  }
};

// =====================================================
// SAFE MS FORMAT
// =====================================================

export const fmtMs = (
  ms?: number | null
) => {

  try {

    if (
      ms === undefined ||
      ms === null ||
      Number.isNaN(ms)
    ) {
      return "0 ms";
    }

    return `${Number(ms).toFixed(0)} ms`;

  } catch (error) {

    console.error("fmtMs ERROR:", error);

    return "0 ms";
  }
};

// =====================================================
// SAFE CONFIDENCE FORMAT
// =====================================================

export const fmtConfidence = (
  c?: number | null
) => {

  try {

    if (
      c === undefined ||
      c === null ||
      Number.isNaN(c)
    ) {
      return "0.00";
    }

    return Number(c).toFixed(2);

  } catch (error) {

    console.error("fmtConfidence ERROR:", error);

    return "0.00";
  }
};

// =====================================================
// SAFE TRACE ID FORMAT
// =====================================================

export const truncId = (
  id?: string | null,
  head = 6,
  tail = 4
) => {

  try {

    if (!id) {
      return "N/A";
    }

    if (
      id.length <=
      head + tail + 1
    ) {
      return id;
    }

    return `${id.slice(0, head)}…${id.slice(-tail)}`;

  } catch (error) {

    console.error("truncId ERROR:", error);

    return "N/A";
  }
};