import {
  format,
  formatDistanceStrict,
  parseISO,
  isValid,
} from "date-fns";

// =====================================================
// SAFE UTC TIME FORMAT
// =====================================================

export const fmtUtc = (
  iso?: string | null,
  pattern = "HH:mm:ss"
) => {

  try {

    if (!iso) {
      return "N/A";
    }

    const parsed = parseISO(iso);

    if (!isValid(parsed)) {
      return "N/A";
    }

    return format(parsed, pattern);

  } catch (error) {

    console.error("fmtUtc ERROR:", error);

    return "N/A";
  }
};

// =====================================================
// SAFE UTC DATE FORMAT
// =====================================================

export const fmtUtcDate = (
  iso?: string | null
) => {

  try {

    if (!iso) {
      return "N/A";
    }

    const parsed = parseISO(iso);

    if (!isValid(parsed)) {
      return "N/A";
    }

    return format(
      parsed,
      "yyyy-MM-dd HH:mm:ss"
    );

  } catch (error) {

    console.error("fmtUtcDate ERROR:", error);

    return "N/A";
  }
};

// =====================================================
// SAFE AGE FORMAT
// =====================================================

export const ageFrom = (
  iso?: string | null,
  now: Date = new Date()
) => {

  try {

    if (!iso) {
      return "N/A";
    }

    const parsed = parseISO(iso);

    if (!isValid(parsed)) {
      return "N/A";
    }

    return formatDistanceStrict(
      parsed,
      now,
      {
        addSuffix: false,
      }
    );

  } catch (error) {

    console.error("ageFrom ERROR:", error);

    return "N/A";
  }
};

// =====================================================
// CURRENT ISO TIME
// =====================================================

export const nowIso = () =>
  new Date().toISOString();

// =====================================================
// CURRENT UTC DISPLAY
// =====================================================

export const nowUtcDisplay = () => {

  try {

    return format(
      new Date(),
      "yyyy-MM-dd HH:mm:ss"
    );

  } catch (error) {

    console.error(
      "nowUtcDisplay ERROR:",
      error
    );

    return "N/A";
  }
};