<script setup lang="ts">
import AppLayout from '@/layouts/AppLayout.vue';
import { dashboard } from '@/routes';
import { type BreadcrumbItem } from '@/types';
import { Head } from '@inertiajs/vue3';
import { computed, reactive, ref, watch } from 'vue';

/* ------------------------- TYPES ------------------------- */
type Match = {
  id: number;
  home_team: string;
  away_team: string;
  match_date?: string; // YYYY-MM-DD
  match_time?: string;
  home_odds?: string;
  draw_odds?: string;
  away_odds?: string;
  match_url?: string;
  league?: string;
};

type H2H = {
  id: number;
  match_id: number;
  home_team: string;
  away_team: string;
  score?: string; // "1-0", "2:2"
};

type Standing = {
  id: number;
  team: string;
  rank: string | number;
  mp?: string | number;
  wins?: string | number;
  draws?: string | number;
  losses?: string | number;
  pts?: string | number;
  gd?: string | number;
  goals?: string;
};
const copiedMaster = ref(false);

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback for older browsers / non-HTTPS contexts
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      ta.style.top = "-9999px";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }
};

const masterTeamsText = computed(() => {
  // Teams only (as you asked)
  return masterCombo.value.matches
    .map((m: any) => `${m.home_team} vs ${m.away_team}`)
    .join("\n");
});

const copyMasterTeams = async () => {
  const txt = masterTeamsText.value.trim();
  if (!txt) return;

  const ok = await copyToClipboard(txt);
  if (ok) {
    copiedMaster.value = true;
    window.setTimeout(() => (copiedMaster.value = false), 1200);
  }
};

const props = defineProps<{
  matches: Match[];
  h2hMatches: H2H[];
  standings: Standing[];
}>();

const breadcrumbs: BreadcrumbItem[] = [{ title: 'Dashboard', href: dashboard().url }];

/* ------------------------- HELPERS ------------------------- */
const normKey = (s: unknown) =>
  String(s ?? '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ');

const clamp = (n: number, min: number, max: number) => Math.max(min, Math.min(max, n));

const toNum = (v: unknown, def = 0) => {
  const n = Number(String(v ?? '').trim().replace(',', '.'));
  return Number.isFinite(n) ? n : def;
};

const sigmoid = (x: number) => 1 / (1 + Math.exp(-x));

const parseScore = (score?: string) => {
  const m = String(score ?? '').match(/^\s*(\d+)\s*[:\-–]\s*(\d+)\s*/);
  return m ? { h: Number(m[1]), a: Number(m[2]), ok: true } : { h: 0, a: 0, ok: false };
};

const dateTodayISO = () => {
  const d = new Date();
  const tz = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - tz).toISOString().slice(0, 10);
};

const deepClone = <T,>(o: T): T => JSON.parse(JSON.stringify(o));

/* ------------------------- UI CLASSES (avoid Tailwind purge) ------------------------- */
const colorText = {
  indigo: 'text-indigo-600',
  rose: 'text-rose-600',
  emerald: 'text-emerald-600',
  slate: 'text-slate-600',
} as const;

const colorAccent = {
  indigo: 'accent-indigo-600',
  rose: 'accent-rose-600',
  emerald: 'accent-emerald-600',
  slate: 'accent-slate-900',
} as const;

/* ------------------------- DEFAULT FILTER STATE ------------------------- */
const DEFAULTS = {
  // panel
  showFilters: true,
  showAdvanced: false,
  collapse: {
    basic: true,
    leagues: true,
    dates: true,
    performance: true,
    advanced: false,
  },

  // filters
  searchTeam: '',
  hideNoData: true,
  strategyFilter: 'all' as 'all' | 'neural-x' | 'top-pick' | 'value',

  minConfidence: 0,
// DEFAULTS
mpRange: { min: 0, max: 80 },

  homeWinRange: { min: 0, max: 100 },
  homeLossRange: { min: 0, max: 100 },
  awayWinRange: { min: 0, max: 100 },
  awayLossRange: { min: 0, max: 100 },

  homeWinsThreshold: 0,
  homeLossesThreshold: 40,
  awayWinsThreshold: 0,
  awayLossesThreshold: 40,

  selectedLeagues: [] as string[],
  searchLeagueQuery: '',
  showLeagueFilter: false,

  minDate: dateTodayISO(),
  maxDate: dateTodayISO(),

  pickFilter: 'all' as 'all' | '1' | 'X' | '2',
  dominanceSideFilter: 'all' as 'all' | 'home' | 'away',
  minDominancePct: 0,

  showOnlyValue: false,
  minValueEdgePct: 0,

  minRankGap: 0,
  minGdGap: 0,
  minH2H: 0,

  pickOddRange: { min: 1.0, max: 100.0 },

  // combos
  showMasterCombo: false,
  targetOdd: 20,
  comboMode: 'normal' as 'normal' | 'home_wins',
  showWeeklyChallenge: false,

  // per-card expanded stats
  openCardId: null as number | null,
};

const state = reactive(deepClone(DEFAULTS));

/* ------------------------- PERSIST (optional, local only) ------------------------- */
const STORAGE_KEY = 'neuralx_filters_v3';
const loadState = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);

    // safe merge (only known keys)
    Object.assign(state, deepClone(DEFAULTS), parsed);

    // prevent UI glitches
    state.showLeagueFilter = false;
    if (!state.minDate && !state.maxDate) {
      // ok
    }
  } catch {
    // ignore
  }
};

const saveState = () => {
  try {
    const payload = deepClone(state);
    // don’t persist dropdown open states
    payload.showLeagueFilter = false;
    payload.openCardId = null;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // ignore
  }
};

loadState();
watch(
  () => state,
  () => saveState(),
  { deep: true }
);

/* ------------------------- FILTER ACTIONS ------------------------- */
const resetFilters = () => {
  const keepPanel = {
    showFilters: state.showFilters,
    showAdvanced: state.showAdvanced,
    collapse: deepClone(state.collapse),
  };

  Object.assign(state, deepClone(DEFAULTS));
  state.showFilters = keepPanel.showFilters;
  state.showAdvanced = keepPanel.showAdvanced;
  state.collapse = keepPanel.collapse;

  // close popovers
  state.showLeagueFilter = false;
};

const setToday = () => {
  const d = dateTodayISO();
  state.minDate = d;
  state.maxDate = d;
};

const setNext7Days = () => {
  const now = new Date();
  const min = now.toISOString().split('T')[0];
  const plus7 = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
  state.minDate = min;
  state.maxDate = plus7;
};

const setAllDates = () => {
  state.minDate = '';
  state.maxDate = '';
};

const toggleSection = (k: keyof typeof DEFAULTS.collapse) => {
  state.collapse[k] = !state.collapse[k];
};

const toggleLeague = (league: string) => {
  const i = state.selectedLeagues.indexOf(league);
  if (i > -1) state.selectedLeagues.splice(i, 1);
  else state.selectedLeagues.push(league);
};

const toggleCard = (id: number) => {
  state.openCardId = state.openCardId === id ? null : id;
};

/* ------------------------- INDEX MAPS ------------------------- */
const standingsMap = computed(() => {
  const m = new Map<string, Standing>();
  for (const s of props.standings ?? []) m.set(normKey(s.team), s);
  return m;
});

const h2hMap = computed(() => {
  const m = new Map<number, H2H[]>();
  for (const h of props.h2hMatches ?? []) {
    if (!m.has(h.match_id)) m.set(h.match_id, []);
    m.get(h.match_id)!.push(h);
  }
  return m;
});

/* ------------------------- TEAM + H2H STATS ------------------------- */
type TeamStats = {
  rank: number;
  mp: number;
  wins: number;
  draws: number;
  losses: number;
  pts: number;
  gd: number;

  ppg: number;
  winRate: number;
  drawRate: number;
  lossRate: number;
  gdPerMatch: number;
};

const getTeamStats = (teamName: string): TeamStats => {
  const s = standingsMap.value.get(normKey(teamName));
  const mp = toNum(s?.mp, 0);
  const wins = toNum(s?.wins, 0);
  const losses = toNum(s?.losses, 0);
  const derivedDraws = mp > 0 ? Math.max(0, mp - wins - losses) : 0;
  const draws = s?.draws != null ? toNum(s.draws, derivedDraws) : derivedDraws;

  const pts = toNum(s?.pts, 0);
  const gd = toNum(s?.gd, 0);
  const rank = toNum(s?.rank, 99);

  const ppg = mp > 0 ? pts / mp : 0;
  const winRate = mp > 0 ? (wins / mp) * 100 : 0;
  const drawRate = mp > 0 ? (draws / mp) * 100 : 0;
  const lossRate = mp > 0 ? (losses / mp) * 100 : 0;
  const gdPerMatch = mp > 0 ? gd / mp : 0;

  return { rank, mp, wins, draws, losses, pts, gd, ppg, winRate, drawRate, lossRate, gdPerMatch };
};

type H2HStats = {
  total: number;
  hWins: number;
  aWins: number;
  draws: number;
  diff: number;
  avgGoals: number;
};

const getH2HStats = (match: Match): H2HStats => {
  const rows = h2hMap.value.get(match.id) || [];
  let total = 0;
  let hWins = 0;
  let aWins = 0;
  let draws = 0;
  let sumGoals = 0;

  for (const r of rows) {
    const { h, a, ok } = parseScore(r.score);
    if (!ok) continue;

    const alignedHomeGoals = normKey(r.home_team) === normKey(match.home_team) ? h : a;
    const alignedAwayGoals = normKey(r.home_team) === normKey(match.home_team) ? a : h;

    total++;
    sumGoals += alignedHomeGoals + alignedAwayGoals;

    if (alignedHomeGoals > alignedAwayGoals) hWins++;
    else if (alignedAwayGoals > alignedHomeGoals) aWins++;
    else draws++;
  }

  return {
    total,
    hWins,
    aWins,
    draws,
    diff: hWins - aWins,
    avgGoals: total > 0 ? sumGoals / total : 0,
  };
};

/* ------------------------- PREDICTION ENGINE (NEURAL-X v2) ------------------------- */
const MARKET_BLEND = 0.20;

type Analysis = {
  pick: '1' | 'X' | '2';
  confidence: number;
  isNeuralXElite: boolean;
  isTopPick: boolean;
  isValuePick: boolean;

  why: string;
  hasData: boolean;

  dominant: { side: 'home' | 'away' | 'none'; index: number; label: string };

  probs: { h: number; d: number; a: number };
  implied: { h: number; d: number; a: number };
  edge: { pickEdge: number; bestEdge: number; bestMarket: '1' | 'X' | '2' };

  gaps: { rankGap: number; rankSigned: number; ppgGap: number; gdGap: number; gdAbs: number };

  home: TeamStats & { isBetterRank: boolean };
  away: TeamStats & { isBetterRank: boolean };
  h2h: H2HStats;
  odds: { h: number; d: number; a: number };
};

const analyzedMatches = computed(() => {
  return (props.matches ?? []).map((match) => {
    const home = getTeamStats(match.home_team);
    const away = getTeamStats(match.away_team);
    const h2h = getH2HStats(match);

    const odds = { h: toNum(match.home_odds, 0), d: toNum(match.draw_odds, 0), a: toNum(match.away_odds, 0) };

    const invH = odds.h > 0 ? 1 / odds.h : 0;
    const invD = odds.d > 0 ? 1 / odds.d : 0;
    const invA = odds.a > 0 ? 1 / odds.a : 0;
    const invSum = invH + invD + invA;

    const implied = {
      h: invSum > 0 ? invH / invSum : 0,
      d: invSum > 0 ? invD / invSum : 0,
      a: invSum > 0 ? invA / invSum : 0,
    };

    const rankSigned = away.rank - home.rank; // + => home better
    const ppgGap = home.ppg - away.ppg;
    const gdGapPerMatch = home.gdPerMatch - away.gdPerMatch;
    const h2hAdv = h2h.diff;

    let strength =
      0.12 * rankSigned +
      1.15 * ppgGap +
      0.95 * gdGapPerMatch +
      0.35 * clamp(h2hAdv, -4, 4) +
      0.18;

    if (h2h.total < 2) strength *= 0.92;

    const baseHome = sigmoid(strength);
    const baseAway = 1 - baseHome;

    const baseDrawRate = clamp(((home.drawRate + away.drawRate) / 2) / 100, 0.10, 0.34);
    const gapFactor = 1 - clamp(Math.abs(baseHome - 0.5) * 2, 0, 0.85);
    let drawProb = clamp(baseDrawRate * (0.55 + 0.65 * gapFactor), 0.07, 0.33);

    const rem = 1 - drawProb;
    let modelH = baseHome * rem;
    let modelA = baseAway * rem;
    let modelD = drawProb;

    const blend = (m: number, p: number) => (1 - MARKET_BLEND) * m + MARKET_BLEND * p;
    modelH = blend(modelH, implied.h);
    modelD = blend(modelD, implied.d);
    modelA = blend(modelA, implied.a);

    const s = modelH + modelD + modelA;
    const probs = s > 0 ? { h: modelH / s, d: modelD / s, a: modelA / s } : { h: 0, d: 0, a: 0 };

    const maxP = Math.max(probs.h, probs.d, probs.a);
    const pick: '1' | 'X' | '2' = maxP === probs.h ? '1' : maxP === probs.a ? '2' : 'X';
    const confidence = clamp(Math.round(maxP * 100), 1, 99);

    const diffHA = probs.h - probs.a;
    const dominantSide: 'home' | 'away' | 'none' = Math.abs(diffHA) >= 0.18 ? (diffHA > 0 ? 'home' : 'away') : 'none';
    const dominanceIndex = clamp(Math.abs(diffHA), 0, 1);

    const edgeH = probs.h - implied.h;
    const edgeD = probs.d - implied.d;
    const edgeA = probs.a - implied.a;

    let bestEdge = edgeH;
    let bestMarket: '1' | 'X' | '2' = '1';
    if (edgeD > bestEdge) {
      bestEdge = edgeD;
      bestMarket = 'X';
    }
    if (edgeA > bestEdge) {
      bestEdge = edgeA;
      bestMarket = '2';
    }

    const pickEdge = pick === '1' ? edgeH : pick === '2' ? edgeA : edgeD;
    const isValuePick = pickEdge >= 0.03;

    const rankAbs = Math.abs(rankSigned);
    const gdAbs = Math.abs(home.gd - away.gd);

    const isNeuralXElite = confidence >= 92 && dominanceIndex >= 0.28 && (rankAbs >= 8 || gdAbs >= 8 || Math.abs(h2hAdv) >= 2);
    const isTopPick = confidence >= 85 && dominanceIndex >= 0.22;

    const hasData = home.mp > 0 || away.mp > 0;

    const reasons: string[] = [];
    if (rankAbs >= 6) reasons.push(`Rank gap ${rankAbs} (${rankSigned > 0 ? 'Home' : 'Away'} avantage)`);
    if (Math.abs(ppgGap) >= 0.35) reasons.push(`PPG gap ${ppgGap > 0 ? '+' : ''}${ppgGap.toFixed(2)}`);
    if (Math.abs(home.gd - away.gd) >= 6) reasons.push(`GD gap ${home.gd - away.gd > 0 ? '+' : ''}${home.gd - away.gd}`);
    if (h2h.total >= 3 && Math.abs(h2hAdv) >= 2) reasons.push(`H2H ${h2h.hWins}-${h2h.draws}-${h2h.aWins}`);
    if (probs.d >= 0.28) reasons.push(`Draw risk (${Math.round(probs.d * 100)}%)`);
    if (isValuePick) reasons.push(`Value +${Math.round(pickEdge * 100)}pp vs marché`);
    if (reasons.length === 0) reasons.push('Match équilibré (profil serré).');

    const dominantLabel =
      dominantSide === 'home' ? `Dominant: ${match.home_team}` : dominantSide === 'away' ? `Dominant: ${match.away_team}` : 'Dominant: Aucun (équilibré)';

    const analysis: Analysis = {
      pick,
      confidence,
      isNeuralXElite,
      isTopPick,
      isValuePick,
      why: reasons.join(' | '),
      hasData,
      dominant: { side: dominantSide, index: dominanceIndex, label: dominantLabel },
      probs,
      implied,
      edge: { pickEdge, bestEdge, bestMarket },
      gaps: {
        rankGap: rankAbs,
        rankSigned,
        ppgGap,
        gdGap: home.gd - away.gd,
        gdAbs,
      },
      home: { ...home, isBetterRank: home.rank < away.rank },
      away: { ...away, isBetterRank: away.rank < home.rank },
      h2h,
      odds,
    };

    return { ...match, analysis } as const;
  });
});

/* ------------------------- COMPUTED LISTS ------------------------- */
const availableLeagues = computed(() => {
  const leagues = new Set<string>();
  for (const m of props.matches ?? []) leagues.add(m.league ? m.league : 'Unknown');
  return Array.from(leagues).sort((a, b) => a.localeCompare(b));
});

const filteredLeaguesList = computed(() => {
  const q = state.searchLeagueQuery.trim().toLowerCase();
  if (!q) return availableLeagues.value;
  return availableLeagues.value.filter((l) => l.toLowerCase().includes(q));
});

const filteredMatches = computed(() => {
  const search = state.searchTeam.trim().toLowerCase();

  return analyzedMatches.value.filter((m) => {
    const a = m.analysis;

    if (state.hideNoData && !a.hasData) return false;

    if (search && !`${m.home_team} ${m.away_team}`.toLowerCase().includes(search)) return false;

    const league = m.league ? m.league : 'Unknown';
    if (state.selectedLeagues.length > 0 && !state.selectedLeagues.includes(league)) return false;

    if (state.minDate && (m.match_date || '') < state.minDate) return false;
    if (state.maxDate && (m.match_date || '') > state.maxDate) return false;

    if (state.strategyFilter === 'neural-x' && !a.isNeuralXElite) return false;
    if (state.strategyFilter === 'top-pick' && !a.isTopPick) return false;
    if (state.strategyFilter === 'value' && !a.isValuePick) return false;

    if (state.minConfidence > 0 && a.confidence < state.minConfidence) return false;

    if (a.home.mp < state.mpRange.min || a.home.mp > state.mpRange.max) return false;
    if (a.away.mp < state.mpRange.min || a.away.mp > state.mpRange.max) return false;

    if (a.home.mp > 0) {
      if (a.home.winRate < state.homeWinRange.min || a.home.winRate > state.homeWinRange.max) return false;
      if (a.home.lossRate < state.homeLossRange.min || a.home.lossRate > state.homeLossRange.max) return false;
      if (a.home.wins < state.homeWinsThreshold) return false;
      if (a.home.losses > state.homeLossesThreshold) return false;
    }
    if (a.away.mp > 0) {
      if (a.away.winRate < state.awayWinRange.min || a.away.winRate > state.awayWinRange.max) return false;
      if (a.away.lossRate < state.awayLossRange.min || a.away.lossRate > state.awayLossRange.max) return false;
      if (a.away.wins < state.awayWinsThreshold) return false;
      if (a.away.losses > state.awayLossesThreshold) return false;
    }

    // Advanced filters (only applied when showAdvanced=true)
    if (state.showAdvanced) {
      if (state.pickFilter !== 'all' && a.pick !== state.pickFilter) return false;

      if (state.dominanceSideFilter !== 'all' && a.dominant.side !== state.dominanceSideFilter) return false;
      if (state.minDominancePct > 0 && a.dominant.index * 100 < state.minDominancePct) return false;

      if (state.showOnlyValue && a.edge.pickEdge * 100 < state.minValueEdgePct) return false;

      if (state.minRankGap > 0 && a.gaps.rankGap < state.minRankGap) return false;
      if (state.minGdGap > 0 && a.gaps.gdAbs < state.minGdGap) return false;

      if (state.minH2H > 0 && a.h2h.total < state.minH2H) return false;

      const pickOdd = a.pick === '1' ? a.odds.h : a.pick === '2' ? a.odds.a : a.odds.d;
      if (pickOdd < state.pickOddRange.min) return false;
      if (pickOdd > state.pickOddRange.max) return false;
    }

    return true;
  });
});

/* ------------------------- ACTIVE FILTER BADGES (when panel hidden) ------------------------- */
const activeBadges = computed(() => {
  const b: string[] = [];

  if (state.searchTeam.trim()) b.push(`Team: ${state.searchTeam.trim()}`);
  if (state.selectedLeagues.length > 0) b.push(`Leagues: ${state.selectedLeagues.length}`);
  if (state.minDate || state.maxDate) b.push(`Dates`);
  if (state.minConfidence > 0) b.push(`Conf ≥ ${state.minConfidence}%`);
  if (state.strategyFilter !== 'all') b.push(`Mode: ${state.strategyFilter}`);

  if (state.showAdvanced) {
    if (state.pickFilter !== 'all') b.push(`Pick: ${state.pickFilter}`);
    if (state.dominanceSideFilter !== 'all') b.push(`Dom: ${state.dominanceSideFilter}`);
    if (state.minDominancePct > 0) b.push(`Dom ≥ ${state.minDominancePct}%`);
    if (state.showOnlyValue) b.push(`Value ≥ ${state.minValueEdgePct}pp`);
    if (state.minRankGap > 0) b.push(`RankGap ≥ ${state.minRankGap}`);
    if (state.minGdGap > 0) b.push(`GDGap ≥ ${state.minGdGap}`);
    if (state.minH2H > 0) b.push(`H2H ≥ ${state.minH2H}`);
  }

  return b.slice(0, 10);
});

/* ------------------------- COMBOS ------------------------- */
const comboOptions = [10, 20, 30, 40, 50];

const setComboMode = (mode: 'normal' | 'home_wins', odd?: number) => {
  state.comboMode = mode;
  if (odd) state.targetOdd = odd;
  state.showMasterCombo = true;
  state.showWeeklyChallenge = false;
};

const toggleWeeklyChallenge = () => {
  state.showWeeklyChallenge = !state.showWeeklyChallenge;
  state.showMasterCombo = false;
};

const masterCombo = computed(() => {
  const target = state.comboMode === 'home_wins' ? 15 : state.targetOdd;
  const sorted = [...filteredMatches.value].sort((a, b) => b.analysis.confidence - a.analysis.confidence);

  let ticket: any[] = [];
  let totalOdd = 1;

  for (const m of sorted) {
    const a = m.analysis;

    let pick = a.pick;
    let odd = pick === '1' ? a.odds.h : pick === '2' ? a.odds.a : a.odds.d;

    if (state.comboMode === 'home_wins') {
      if (a.pick !== '1') continue;
      if (a.odds.h < 1.3) continue;
      if (a.confidence < 82) continue;
      pick = '1';
      odd = a.odds.h;
    } else {
      if (a.confidence < 80) continue;
      if (odd < 1.2) continue;
      if (a.edge.pickEdge < -0.01) continue;
    }

    if (totalOdd * odd > target * 1.2) continue;

    ticket.push({ ...m, selectedOdd: odd, selectedPick: pick });
    totalOdd *= odd;

    if (totalOdd >= target * 0.9) break;
  }

  return { matches: ticket, totalOdd: totalOdd.toFixed(2), targetOdd: target };
});

const getWeeklyChallengeCombo = (matches: typeof analyzedMatches.value) => {
  const weeklyMatches = new Map<string, any[]>();

  const highConfidenceHomeWins = matches.filter(
    (m) => m.analysis.pick === '1' && m.analysis.confidence >= 85 && m.analysis.odds.h >= 1.3 && !!m.match_date
  );

  for (const m of highConfidenceHomeWins) {
    const date = m.match_date!;
    if (!weeklyMatches.has(date)) weeklyMatches.set(date, []);
    weeklyMatches.get(date)!.push(m);
  }

  let ticket: any[] = [];
  let totalOdd = 1;

  const sortedDates = Array.from(weeklyMatches.keys()).sort();
  for (const date of sortedDates) {
    const daily = weeklyMatches.get(date)!.sort((a, b) => b.analysis.confidence - a.analysis.confidence).slice(0, 2);
    for (const m of daily) {
      const odd = m.analysis.odds.h;
      ticket.push({ ...m, selectedOdd: odd, selectedPick: '1' });
      totalOdd *= odd;
    }
  }

  return { matches: ticket, totalOdd: totalOdd.toFixed(2), targetOdd: 500 };
};

const weeklyChallengeCombo = computed(() => getWeeklyChallengeCombo(analyzedMatches.value));
</script>

<template>
 
    <Head title="Ultimate Neural Dashboard" />

    <div class="min-h-screen bg-gray-50 p-4 lg:p-10 font-sans text-slate-900">
      <div class="max-w-[1600px] mx-auto space-y-10">

        <!-- Header -->
        <header class="flex flex-col lg:flex-row justify-between items-center gap-6">
          <div class="flex items-center gap-4">
            <div class="w-16 h-16 bg-slate-900 rounded-3xl flex items-center justify-center text-white text-4xl shadow-2xl shadow-slate-200">🧠</div>
            <h1 class="text-6xl font-black tracking-tighter text-slate-900">
              Ultimate<span class="text-indigo-600">Neural</span><span class="text-slate-300 ml-2">Dashboard</span>
            </h1>
          </div>

          <div class="flex flex-wrap items-center gap-4 justify-center">
            <button
              @click="state.showFilters = !state.showFilters"
              :class="[
                'px-8 py-4 rounded-3xl font-black text-lg transition-all shadow-xl flex items-center gap-3 transform hover:scale-105',
                state.showFilters ? 'bg-white text-slate-900 border border-slate-200 shadow-slate-200' : 'bg-slate-900 text-white shadow-slate-200',
              ]"
            >
              🎛️ Filters
              <span class="px-3 py-1 rounded-2xl text-[11px] font-black"
                :class="state.showFilters ? 'bg-slate-100 text-slate-600' : 'bg-white/10 text-white/80'">
                {{ activeBadges.length }}
              </span>
            </button>

            <button
              @click="toggleWeeklyChallenge"
              :class="[
                'px-10 py-5 rounded-3xl font-black text-xl transition-all shadow-xl flex items-center gap-3 transform hover:scale-105',
                state.showWeeklyChallenge ? 'bg-emerald-600 text-white shadow-emerald-200' : 'bg-slate-900 text-white shadow-slate-200',
              ]"
            >
              <span>⚔️</span> Titan Weekly Challenge
            </button>

            <div class="px-6 py-3 bg-white rounded-2xl shadow-sm border border-slate-200 font-black text-slate-400">
              Matchs: <span class="text-indigo-600">{{ filteredMatches.length }}</span>
            </div>
          </div>
        </header>

        <!-- Active badges when filters hidden -->
        <div v-if="!state.showFilters && activeBadges.length > 0" class="bg-white/70 backdrop-blur border border-white/80 rounded-3xl p-6 shadow-lg">
          <div class="flex flex-wrap gap-2 items-center">
            <div class="text-[11px] font-black text-slate-400 uppercase tracking-widest mr-2">Active</div>
            <span v-for="b in activeBadges" :key="b" class="px-4 py-2 rounded-2xl bg-slate-50 border border-slate-200 text-[11px] font-black text-slate-700">
              {{ b }}
            </span>
            <button @click="resetFilters" class="ml-auto px-4 py-2 rounded-2xl bg-rose-600 text-white text-[11px] font-black shadow hover:opacity-90">
              Reset
            </button>
          </div>
        </div>

        <!-- Combo Controls -->
        <div class="flex flex-wrap gap-4 justify-center lg:justify-start">
          <button
            v-for="odd in comboOptions"
            :key="odd"
            @click="setComboMode('normal', odd)"
            :class="[
              'px-6 py-3 rounded-full font-black text-sm transition-all',
              state.comboMode === 'normal' && state.targetOdd === odd && state.showMasterCombo ? 'bg-indigo-600 text-white shadow-lg' : 'bg-white text-slate-900 border border-slate-200 hover:bg-slate-50',
            ]"
          >
            Combo x{{ odd }}
          </button>

          <button
            @click="setComboMode('home_wins')"
            :class="[
              'px-6 py-3 rounded-full font-black text-sm transition-all',
              state.comboMode === 'home_wins' && state.showMasterCombo ? 'bg-emerald-600 text-white shadow-lg' : 'bg-white text-slate-900 border border-slate-200 hover:bg-slate-50',
            ]"
          >
            🏆 Spécial x15 (Home Wins)
          </button>
        </div>

        <!-- Titan Weekly Challenge -->
        <div v-if="state.showWeeklyChallenge" class="bg-white/50 backdrop-blur-xl border border-white/80 rounded-3xl p-12 text-slate-900 shadow-3xl animate-slide-up relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-full bg-white/30 -z-10"></div>

          <div class="flex justify-between items-center mb-12 relative z-10">
            <div>
              <h2 class="text-5xl font-black tracking-tighter">Titan <span class="text-emerald-600">Weekly Challenge</span></h2>
              <p class="text-slate-600 font-bold text-lg">2 Home Wins par jour, objectif cote >500</p>
            </div>
            <div class="text-right">
              <div class="text-6xl font-black text-emerald-600 tracking-tighter">x{{ weeklyChallengeCombo.totalOdd }}</div>
              <div class="text-[10px] font-black uppercase tracking-widest text-slate-500">Cote Totale Combinée (Cible: >{{ weeklyChallengeCombo.targetOdd }})</div>
            </div>

          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-8 relative z-10">
            <a v-for="m in weeklyChallengeCombo.matches" :key="m.id" :href="m.match_url" target="_blank"
               class="bg-white/80 border border-white/90 rounded-3xl p-8 backdrop-blur-sm hover:bg-white transition-all group shadow-lg">
              <div class="flex justify-between items-center mb-6">
                <span class="text-[10px] font-black text-emerald-600 uppercase">{{ m.match_date }} • {{ m.match_time }}</span>
                <span class="px-4 py-1.5 bg-slate-900 text-white rounded-xl text-[10px] font-black">Pick: {{ m.selectedPick }} (@{{ m.selectedOdd }})</span>
              </div>
              <div class="font-black text-xl mb-3 truncate group-hover:text-emerald-600 transition-colors">{{ m.home_team }} vs {{ m.away_team }}</div>
              <p class="text-[11px] text-slate-600 font-bold leading-relaxed italic">"{{ m.analysis.why }}"</p>
              <div class="mt-6 text-[9px] font-black text-slate-400 uppercase group-hover:text-slate-900">Voir Détails →</div>
            </a>
          </div>

          <button @click="state.showWeeklyChallenge = false" class="absolute top-8 right-8 text-3xl opacity-30 hover:opacity-100 transition-opacity">✕</button>
        </div>

        <!-- Master Combo -->
        <div v-if="state.showMasterCombo" class="bg-white/50 backdrop-blur-xl border border-white/80 rounded-3xl p-12 text-slate-900 shadow-3xl animate-slide-up relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-full bg-white/30 -z-10"></div>

          <div class="flex justify-between items-center mb-12 relative z-10">
            <div>
              <h2 class="text-5xl font-black tracking-tighter">
                Daily <span :class="state.comboMode === 'home_wins' ? 'text-emerald-600' : 'text-indigo-600'">Master Combo</span>
              </h2>
              <p class="text-slate-600 font-bold text-lg">Sélection IA des matchs à haute confiance pour une cote cible de x{{ masterCombo.targetOdd }}</p>
            </div>
            <div class="text-right">
              <div class="text-6xl font-black text-indigo-600 tracking-tighter">x{{ masterCombo.totalOdd }}</div>
              <div class="text-[10px] font-black uppercase tracking-widest text-slate-500">Cote Totale Combinée</div>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-8 relative z-10">
            <a v-for="m in masterCombo.matches" :key="m.id" :href="m.match_url" target="_blank"
               class="bg-white/80 border border-white/90 rounded-3xl p-8 backdrop-blur-sm hover:bg-white transition-all group shadow-lg">
              <div class="flex justify-between items-center mb-6">
                <span class="text-[10px] font-black text-indigo-600 uppercase">{{ m.match_date }} • {{ m.match_time }}</span>
                <span class="px-4 py-1.5 bg-slate-900 text-white rounded-xl text-[10px] font-black">Pick: {{ m.selectedPick }} (@{{ m.selectedOdd }})</span>
              </div>
              <div class="font-black text-xl mb-3 truncate group-hover:text-indigo-600 transition-colors">{{ m.home_team }} vs {{ m.away_team }}</div>
              <p class="text-[11px] text-slate-600 font-bold leading-relaxed italic">"{{ m.analysis.why }}"</p>
              <div class="mt-6 text-[9px] font-black text-slate-400 uppercase group-hover:text-slate-900">Voir Détails →</div>
            </a>
          </div>

          <button @click="state.showMasterCombo = false" class="absolute top-8 right-8 text-3xl opacity-30 hover:opacity-100 transition-opacity">✕</button>
        </div>

        <!-- Strategy Tiles -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-8">
          <button
            v-for="s in [
              { id: 'all', label: 'Tous les Matchs', icon: '🌍' },
              { id: 'neural-x', label: 'Neural-X Elite', icon: '💎' },
              { id: 'top-pick', label: 'Top Picks (85%+)', icon: '⭐' },
              { id: 'value', label: 'Value Picks', icon: '📈' },
            ]"
            :key="s.id"
            @click="state.strategyFilter = s.id"
            :class="[
              'p-8 rounded-3xl border-2 transition-all duration-300 flex items-center gap-6 text-left relative overflow-hidden group',
              state.strategyFilter === s.id ? 'bg-white border-indigo-600 shadow-xl transform scale-[1.02]' : 'bg-white border-transparent shadow-sm hover:border-slate-200',
            ]"
          >
            <span class="text-5xl group-hover:scale-110 transition-transform duration-300">{{ s.icon }}</span>
            <div class="flex flex-col">
              <span class="text-[11px] font-black text-slate-400 uppercase tracking-widest">Stratégie</span>
              <span class="text-2xl font-black text-slate-900">{{ s.label }}</span>
            </div>
            <div v-if="state.strategyFilter === s.id" class="absolute top-8 right-8 w-4 h-4 bg-indigo-600 rounded-full animate-ping"></div>
          </button>
        </div>

        <!-- FILTER PANEL (collapsible + hide/show) -->
        <transition name="fade-slide">
          <div v-if="state.showFilters" class="bg-white rounded-3xl shadow-lg border border-slate-100 p-10 space-y-10">

            <!-- Panel header actions -->
            <div class="flex flex-col lg:flex-row gap-4 justify-between items-start lg:items-center">
              <div>
                <div class="text-[11px] font-black text-slate-400 uppercase tracking-widest">Control Center</div>
                <div class="text-3xl font-black text-slate-900 mt-2">Filtres Neural-X</div>
              </div>

              <div class="flex gap-3 flex-wrap">
                <button @click="resetFilters" class="px-6 py-3 rounded-2xl bg-rose-600 text-white font-black shadow hover:opacity-90">Reset</button>
                <button @click="state.showAdvanced = !state.showAdvanced"
                        :class="['px-6 py-3 rounded-2xl font-black shadow border',
                          state.showAdvanced ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-900 border-slate-200 hover:bg-slate-50']">
                  {{ state.showAdvanced ? 'Hide Advanced' : 'Show Advanced' }}
                </button>
              </div>
            </div>

            <!-- BASIC SECTION -->
            <div class="bg-slate-50/60 rounded-3xl border border-slate-100 p-8">
              <button @click="toggleSection('basic')" class="w-full flex items-center justify-between">
                <div class="text-left">
                  <div class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Section</div>
                  <div class="text-2xl font-black text-slate-900">Basic</div>
                </div>
                <div class="text-slate-500 font-black">{{ state.collapse.basic ? '▼' : '▲' }}</div>
              </button>

              <div v-if="state.collapse.basic" class="mt-8 grid grid-cols-1 xl:grid-cols-4 gap-10">
                <!-- Team Search -->
                <div class="relative group">
                  <label class="text-[11px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-3 block">Rechercher Équipe</label>
                  <input v-model="state.searchTeam" type="text" placeholder="Nom de l'équipe..."
                         class="w-full pl-14 pr-8 py-5 bg-white border border-slate-100 rounded-2xl focus:ring-4 focus:ring-indigo-500/10 transition-all font-bold text-slate-900">
                  <span class="absolute left-5 bottom-5 text-2xl opacity-30 group-focus-within:opacity-100">🔍</span>
                </div>

                <!-- Confidence -->
                <div class="flex flex-col gap-5">
                  <div class="flex justify-between items-end px-2">
                    <label class="text-[11px] font-black text-slate-400 uppercase tracking-widest">Min Confidence</label>
                    <span class="text-2xl font-black text-indigo-600">{{ state.minConfidence }}%</span>
                  </div>
                  <input type="range" v-model.number="state.minConfidence" min="0" max="99"
                         class="w-full h-2.5 bg-white rounded-lg appearance-none cursor-pointer accent-indigo-600">
                </div>

                <!-- MP range -->
                <div class="flex flex-col gap-5">
                  <div class="flex justify-between items-end px-2">
                    <label class="text-[11px] font-black text-slate-400 uppercase tracking-widest">Matchs Joués (MP)</label>
                    <span class="text-2xl font-black text-indigo-600">{{ state.mpRange.min }} - {{ state.mpRange.max }}</span>
                  </div>
                  <div class="flex gap-5">
                    <input type="range" v-model.number="state.mpRange.min" min="0" max="80" class="flex-1 h-2.5 bg-white rounded-lg appearance-none cursor-pointer accent-indigo-600">
                    <input type="range" v-model.number="state.mpRange.max" min="0" max="80" class="flex-1 h-2.5 bg-white rounded-lg appearance-none cursor-pointer accent-indigo-600">
                  </div>
                </div>

                <!-- Data Guard -->
                <div class="flex items-center justify-between px-6 bg-white rounded-2xl py-5 border border-slate-100 self-end">
                  <div class="flex flex-col">
                    <span class="text-[11px] font-black text-slate-400 uppercase tracking-widest">Data Guard</span>
                    <span class="text-base font-black text-slate-900">Masquer Sans Données</span>
                  </div>
                  <button @click="state.hideNoData = !state.hideNoData"
                          :class="['w-16 h-9 rounded-full transition-all relative', state.hideNoData ? 'bg-indigo-600' : 'bg-slate-300']">
                    <div :class="['absolute top-1 w-7 h-7 bg-white rounded-full transition-all shadow-md', state.hideNoData ? 'right-1' : 'left-1']"></div>
                  </button>
                </div>
              </div>
            </div>

            <!-- LEAGUES SECTION -->
            <div class="bg-slate-50/60 rounded-3xl border border-slate-100 p-8">
              <button @click="toggleSection('leagues')" class="w-full flex items-center justify-between">
                <div class="text-left">
                  <div class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Section</div>
                  <div class="text-2xl font-black text-slate-900">Leagues</div>
                </div>
                <div class="text-slate-500 font-black">{{ state.collapse.leagues ? '▼' : '▲' }}</div>
              </button>

              <div v-if="state.collapse.leagues" class="mt-8 grid grid-cols-1 xl:grid-cols-2 gap-10">
                <div class="relative">
                  <label class="text-[11px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-3 block">Filtrer par Ligues ({{ state.selectedLeagues.length }})</label>
                  <button @click="state.showLeagueFilter = !state.showLeagueFilter"
                          class="w-full px-6 py-5 bg-white rounded-2xl font-bold text-slate-900 text-left flex justify-between items-center border border-slate-100">
                    <span>{{ state.selectedLeagues.length === 0 ? 'Toutes les ligues' : state.selectedLeagues.length + ' sélectionnées' }}</span>
                    <span class="text-xs transition-transform" :class="{ 'rotate-180': state.showLeagueFilter }">▼</span>
                  </button>

                  <div v-if="state.showLeagueFilter" class="absolute z-50 mt-2 w-full max-h-96 overflow-y-auto bg-white border border-slate-200 rounded-2xl shadow-2xl p-6 space-y-4">
                    <div class="sticky top-0 bg-white pb-4 border-b border-slate-100 space-y-4">
                      <div class="flex justify-between items-center">
                        <button @click="state.selectedLeagues = []" class="text-[10px] font-black text-indigo-600 uppercase">Tout Décocher</button>
                        <button @click="state.showLeagueFilter = false" class="text-[10px] font-black text-slate-400 uppercase">Fermer</button>
                      </div>
                      <input v-model="state.searchLeagueQuery" type="text" placeholder="Rechercher une ligue..."
                             class="w-full px-4 py-3 bg-slate-50 border-none rounded-xl text-sm font-bold focus:ring-2 focus:ring-indigo-500/20">
                    </div>

                    <div class="space-y-2">
                      <div v-for="league in filteredLeaguesList" :key="league" @click="toggleLeague(league)"
                           class="flex items-center gap-3 p-3 hover:bg-slate-50 rounded-xl cursor-pointer transition-colors group">
                        <div class="w-6 h-6 border-2 rounded-lg flex items-center justify-center transition-all"
                             :class="state.selectedLeagues.includes(league) ? 'bg-indigo-600 border-indigo-600' : 'border-slate-200 group-hover:border-indigo-300'">
                          <span v-if="state.selectedLeagues.includes(league)" class="text-white text-xs">✓</span>
                        </div>
                        <span class="text-sm font-black text-slate-700">{{ league }}</span>
                      </div>

                      <div v-if="filteredLeaguesList.length === 0" class="text-center py-10 text-slate-400 font-bold text-sm italic">
                        Aucune ligue trouvée...
                      </div>
                    </div>
                  </div>
                </div>

                <div class="bg-white rounded-2xl border border-slate-100 p-6">
                  <div class="text-[11px] font-black text-slate-400 uppercase tracking-widest">Selected</div>
                  <div class="mt-4 flex flex-wrap gap-2">
                    <span v-if="state.selectedLeagues.length === 0" class="text-sm font-bold text-slate-500 italic">Toutes les ligues</span>
                    <span v-for="l in state.selectedLeagues" :key="l"
                          class="px-4 py-2 rounded-2xl bg-slate-50 border border-slate-200 text-[11px] font-black text-slate-700">
                      {{ l }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- DATES SECTION -->
            <div class="bg-slate-50/60 rounded-3xl border border-slate-100 p-8">
              <button @click="toggleSection('dates')" class="w-full flex items-center justify-between">
                <div class="text-left">
                  <div class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Section</div>
                  <div class="text-2xl font-black text-slate-900">Dates</div>
                </div>
                <div class="text-slate-500 font-black">{{ state.collapse.dates ? '▼' : '▲' }}</div>
              </button>

              <div v-if="state.collapse.dates" class="mt-8 grid grid-cols-1 xl:grid-cols-2 gap-10">
                <div class="flex flex-col gap-5">
                  <div class="flex items-center justify-between px-2">
                    <label class="text-[11px] font-black text-slate-400 uppercase tracking-widest">Plage de Dates</label>
                    <div class="flex gap-2">
                      <button @click="setToday" class="px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-[10px] font-black text-slate-600 hover:bg-slate-50">Today</button>
                      <button @click="setNext7Days" class="px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-[10px] font-black text-slate-600 hover:bg-slate-50">+7D</button>
                      <button @click="setAllDates" class="px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-[10px] font-black text-slate-600 hover:bg-slate-50">All</button>
                    </div>
                  </div>
                  <div class="flex gap-3">
                    <input v-model="state.minDate" type="date" class="flex-1 bg-white border border-slate-100 rounded-2xl p-4 font-bold text-sm" />
                    <input v-model="state.maxDate" type="date" class="flex-1 bg-white border border-slate-100 rounded-2xl p-4 font-bold text-sm" />
                  </div>
                </div>

                <div class="bg-white rounded-2xl border border-slate-100 p-6">
                  <div class="text-[11px] font-black text-slate-400 uppercase tracking-widest">Current Range</div>
                  <div class="mt-4 text-lg font-black text-slate-900">
                    <span class="text-indigo-600">{{ state.minDate || '—' }}</span>
                    <span class="text-slate-400 mx-2">→</span>
                    <span class="text-indigo-600">{{ state.maxDate || '—' }}</span>
                  </div>
                  <div class="mt-3 text-sm font-bold text-slate-500">
                    Tip: choose “All” to see future matches without limit.
                  </div>
                </div>
              </div>
            </div>

            <!-- PERFORMANCE SECTION -->
            <div class="bg-slate-50/60 rounded-3xl border border-slate-100 p-8">
              <button @click="toggleSection('performance')" class="w-full flex items-center justify-between">
                <div class="text-left">
                  <div class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Section</div>
                  <div class="text-2xl font-black text-slate-900">Performance</div>
                </div>
                <div class="text-slate-500 font-black">{{ state.collapse.performance ? '▼' : '▲' }}</div>
              </button>

              <div v-if="state.collapse.performance" class="mt-8 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-10">
                <div v-for="r in [
                      { l: 'Taux Victoire Domicile %', v: state.homeWinRange, t: 'indigo', a: 'indigo' },
                      { l: 'Taux Défaite Domicile %', v: state.homeLossRange, t: 'rose', a: 'rose' },
                      { l: 'Taux Victoire Extérieur %', v: state.awayWinRange, t: 'indigo', a: 'indigo' },
                      { l: 'Taux Défaite Extérieur %', v: state.awayLossRange, t: 'rose', a: 'rose' },
                    ]"
                    :key="r.l" class="space-y-5">
                  <div class="flex justify-between items-center">
                    <label class="text-[11px] font-black text-slate-400 uppercase">{{ r.l }}</label>
                    <span :class="['text-sm font-black', colorText[r.t as keyof typeof colorText]]">{{ r.v.min }}% - {{ r.v.max }}%</span>
                  </div>
                  <div class="flex gap-5">
                    <input type="range" v-model.number="r.v.min" min="0" max="100"
                           :class="['flex-1 h-2 bg-white rounded-lg appearance-none', colorAccent[r.a as keyof typeof colorAccent]]" />
                    <input type="range" v-model.number="r.v.max" min="0" max="100"
                           :class="['flex-1 h-2 bg-white rounded-lg appearance-none', colorAccent[r.a as keyof typeof colorAccent]]" />
                  </div>
                </div>

                <div class="space-y-5">
                  <div class="flex justify-between items-center">
                    <label class="text-[11px] font-black text-slate-400 uppercase">Home Wins ></label>
                    <span class="text-sm font-black text-emerald-600">{{ state.homeWinsThreshold }}</span>
                  </div>
                  <input type="range" v-model.number="state.homeWinsThreshold" min="0" max="40" class="w-full h-2 bg-white rounded-lg appearance-none accent-emerald-600" />
                </div>

                <div class="space-y-5">
                  <div class="flex justify-between items-center">
                    <label class="text-[11px] font-black text-slate-400 uppercase">Home Losses <</label>
                    <span class="text-sm font-black text-rose-600">{{ state.homeLossesThreshold }}</span>
                  </div>
                  <input type="range" v-model.number="state.homeLossesThreshold" min="0" max="40" class="w-full h-2 bg-white rounded-lg appearance-none accent-rose-600" />
                </div>

                <div class="space-y-5">
                  <div class="flex justify-between items-center">
                    <label class="text-[11px] font-black text-slate-400 uppercase">Away Wins ></label>
                    <span class="text-sm font-black text-emerald-600">{{ state.awayWinsThreshold }}</span>
                  </div>
                  <input type="range" v-model.number="state.awayWinsThreshold" min="0" max="40" class="w-full h-2 bg-white rounded-lg appearance-none accent-emerald-600" />
                </div>

                <div class="space-y-5">
                  <div class="flex justify-between items-center">
                    <label class="text-[11px] font-black text-slate-400 uppercase">Away Losses <</label>
                    <span class="text-sm font-black text-rose-600">{{ state.awayLossesThreshold }}</span>
                  </div>
                  <input type="range" v-model.number="state.awayLossesThreshold" min="0" max="40" class="w-full h-2 bg-white rounded-lg appearance-none accent-rose-600" />
                </div>
              </div>
            </div>

            <!-- ADVANCED SECTION -->
            <div v-if="state.showAdvanced" class="bg-slate-50/60 rounded-3xl border border-slate-100 p-8">
              <button @click="toggleSection('advanced')" class="w-full flex items-center justify-between">
                <div class="text-left">
                  <div class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Section</div>
                  <div class="text-2xl font-black text-slate-900">Advanced</div>
                </div>
                <div class="text-slate-500 font-black">{{ state.collapse.advanced ? '▼' : '▲' }}</div>
              </button>

              <div v-if="state.collapse.advanced" class="mt-8 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-10">
                <!-- Pick -->
                <div class="space-y-4">
                  <label class="text-[11px] font-black text-slate-400 uppercase tracking-widest ml-2">Pick</label>
                  <div class="flex gap-2">
                    <button @click="state.pickFilter='all'" :class="['flex-1 py-3 rounded-2xl font-black text-sm', state.pickFilter==='all' ? 'bg-slate-900 text-white' : 'bg-white text-slate-700 border border-slate-200']">All</button>
                    <button @click="state.pickFilter='1'" :class="['flex-1 py-3 rounded-2xl font-black text-sm', state.pickFilter==='1' ? 'bg-indigo-600 text-white' : 'bg-white text-slate-700 border border-slate-200']">1</button>
                    <button @click="state.pickFilter='X'" :class="['flex-1 py-3 rounded-2xl font-black text-sm', state.pickFilter==='X' ? 'bg-slate-600 text-white' : 'bg-white text-slate-700 border border-slate-200']">X</button>
                    <button @click="state.pickFilter='2'" :class="['flex-1 py-3 rounded-2xl font-black text-sm', state.pickFilter==='2' ? 'bg-rose-500 text-white' : 'bg-white text-slate-700 border border-slate-200']">2</button>
                  </div>
                </div>

                <!-- Dominance -->
                <div class="space-y-4">
                  <div class="flex justify-between items-center">
                    <label class="text-[11px] font-black text-slate-400 uppercase tracking-widest ml-2">Dominance</label>
                    <span class="text-sm font-black text-indigo-600">{{ state.minDominancePct }}%</span>
                  </div>
                  <div class="flex gap-2">
                    <button @click="state.dominanceSideFilter='all'" :class="['flex-1 py-3 rounded-2xl font-black text-sm', state.dominanceSideFilter==='all' ? 'bg-slate-900 text-white' : 'bg-white text-slate-700 border border-slate-200']">All</button>
                    <button @click="state.dominanceSideFilter='home'" :class="['flex-1 py-3 rounded-2xl font-black text-sm', state.dominanceSideFilter==='home' ? 'bg-indigo-600 text-white' : 'bg-white text-slate-700 border border-slate-200']">Home</button>
                    <button @click="state.dominanceSideFilter='away'" :class="['flex-1 py-3 rounded-2xl font-black text-sm', state.dominanceSideFilter==='away' ? 'bg-rose-500 text-white' : 'bg-white text-slate-700 border border-slate-200']">Away</button>
                  </div>
                  <input type="range" v-model.number="state.minDominancePct" min="0" max="100" class="w-full h-2 bg-white rounded-lg appearance-none accent-indigo-600" />
                </div>

                <!-- Value -->
                <div class="space-y-4">
                  <div class="flex justify-between items-center">
                    <label class="text-[11px] font-black text-slate-400 uppercase tracking-widest ml-2">Value Edge</label>
                    <span class="text-sm font-black text-emerald-600">+{{ state.minValueEdgePct }}pp</span>
                  </div>

                  <div class="flex items-center justify-between px-4 bg-white rounded-2xl py-3 border border-slate-200">
                    <div class="text-sm font-black text-slate-900">Only Value</div>
                    <button @click="state.showOnlyValue = !state.showOnlyValue"
                            :class="['w-14 h-8 rounded-full transition-all relative', state.showOnlyValue ? 'bg-emerald-600' : 'bg-slate-300']">
                      <div :class="['absolute top-1 w-6 h-6 bg-white rounded-full transition-all shadow-md', state.showOnlyValue ? 'right-1' : 'left-1']"></div>
                    </button>
                  </div>

                  <input type="range" v-model.number="state.minValueEdgePct" min="0" max="20" class="w-full h-2 bg-white rounded-lg appearance-none accent-emerald-600" />
                </div>

                <!-- Gaps + H2H -->
                <div class="space-y-4">
                  <div class="grid grid-cols-2 gap-3">
                    <div>
                      <label class="text-[11px] font-black text-slate-400 uppercase tracking-widest ml-2">Min Rank Gap</label>
                      <input v-model.number="state.minRankGap" type="number" min="0" class="w-full px-4 py-3 bg-white rounded-2xl font-black border border-slate-200" />
                    </div>
                    <div>
                      <label class="text-[11px] font-black text-slate-400 uppercase tracking-widest ml-2">Min GD Gap</label>
                      <input v-model.number="state.minGdGap" type="number" min="0" class="w-full px-4 py-3 bg-white rounded-2xl font-black border border-slate-200" />
                    </div>
                  </div>
                  <div>
                    <label class="text-[11px] font-black text-slate-400 uppercase tracking-widest ml-2">Min H2H (valid)</label>
                    <input v-model.number="state.minH2H" type="number" min="0" class="w-full px-4 py-3 bg-white rounded-2xl font-black border border-slate-200" />
                  </div>
                </div>

                <!-- Odds range -->
                <div class="space-y-4 md:col-span-2">
                  <div class="flex justify-between items-center">
                    <label class="text-[11px] font-black text-slate-400 uppercase tracking-widest ml-2">Pick Odds Range</label>
                    <span class="text-sm font-black text-slate-900">{{ state.pickOddRange.min.toFixed(2) }} - {{ state.pickOddRange.max.toFixed(2) }}</span>
                  </div>
                  <div class="flex gap-5">
                    <input type="range" v-model.number="state.pickOddRange.min" min="1" max="50" step="0.1" class="flex-1 h-2 bg-white rounded-lg appearance-none accent-slate-900" />
                    <input type="range" v-model.number="state.pickOddRange.max" min="1" max="100" step="0.1" class="flex-1 h-2 bg-white rounded-lg appearance-none accent-slate-900" />
                  </div>
                </div>

              </div>
            </div>

          </div>
        </transition>

        <!-- Matches Grid -->
        <div v-if="filteredMatches.length > 0" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-10">
          <div v-for="(match, index) in filteredMatches" :key="match.id"
               :style="{ animationDelay: `${index * 0.05}s` }"
               class="neural-card group bg-white/80 backdrop-blur-md border border-white/90 shadow-xl rounded-3xl p-10 hover:shadow-2xl transition-all duration-500 hover:-translate-y-2 relative overflow-hidden">

            <div v-if="match.analysis.isNeuralXElite" class="absolute -right-16 top-10 rotate-45 bg-slate-900 text-white text-[10px] font-black py-2 px-20 shadow-2xl z-10">NEURAL-X ELITE</div>
            <div v-else-if="match.analysis.isTopPick" class="absolute -right-16 top-10 rotate-45 bg-amber-500 text-white text-[10px] font-black py-2 px-20 shadow-2xl z-10">TOP PICK</div>
            <div v-if="match.analysis.isValuePick" class="absolute left-10 top-8 bg-emerald-600 text-white text-[10px] font-black py-2 px-4 rounded-2xl shadow-lg z-10">VALUE</div>

            <div class="flex justify-between items-center mb-10">
              <div class="px-6 py-2 bg-slate-900 rounded-full text-[11px] font-black uppercase tracking-widest text-white">
                {{ match.match_date }} • {{ match.match_time }}
              </div>
              <div class="flex items-center gap-4">
                <div class="text-4xl font-black text-indigo-600 tracking-tighter">{{ match.analysis.confidence }}%</div>
                <div :class="[
                      'w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-black text-white shadow-lg',
                      match.analysis.pick === '1' ? 'bg-indigo-600' : (match.analysis.pick === '2' ? 'bg-rose-500' : 'bg-slate-500')
                    ]">
                  {{ match.analysis.pick }}
                </div>
              </div>
            </div>

            <div class="mb-8 flex items-center justify-between gap-4">
              <div class="text-[10px] font-black uppercase tracking-widest text-slate-400">{{ match.analysis.dominant.label }}</div>
              <div class="px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-100 text-[10px] font-black text-slate-600">
                Dom: <span class="text-slate-900">{{ Math.round(match.analysis.dominant.index * 100) }}%</span>
              </div>
            </div>

            <!-- Teams -->
            <div class="flex items-center justify-between gap-6 mb-10">
              <div class="flex-1 text-center space-y-4">
                <div class="relative w-24 h-24 mx-auto">
                  <div :class="[
                        'w-full h-full rounded-3xl flex items-center justify-center text-4xl font-black shadow-inner transition-all duration-500',
                        match.analysis.home.isBetterRank ? 'bg-indigo-50 text-indigo-600 border-4 border-indigo-200 animate-pulse-rank' : 'bg-slate-50 text-slate-900'
                      ]">
                    {{ match.home_team.charAt(0) }}
                  </div>
                  <div class="absolute -bottom-2 -right-2 bg-slate-900 text-white text-xs font-black px-3 py-1.5 rounded-xl shadow-xl">
                    #{{ match.analysis.home.rank || '?' }}
                  </div>
                </div>
                <div class="font-black text-slate-900 text-lg truncate">{{ match.home_team }}</div>
                <div class="flex flex-col gap-2">
                  <div class="flex justify-center gap-2">
                    <span class="text-[11px] font-black px-3 py-1 bg-emerald-100 text-emerald-600 rounded-lg">{{ Math.round(match.analysis.home.winRate) }}% V</span>
                    <span class="text-[11px] font-black px-3 py-1 bg-rose-100 text-rose-600 rounded-lg">{{ Math.round(match.analysis.home.lossRate) }}% D</span>
                  </div>
                  <div class="text-[10px] font-black text-slate-400 uppercase">
                    {{ match.analysis.home.wins }}V - {{ match.analysis.home.losses }}D |
                    <span :class="match.analysis.home.gd > 0 ? 'text-emerald-600' : 'text-rose-500'">{{ match.analysis.home.gd }} GD</span>
                  </div>
                </div>
              </div>

              <div class="flex flex-col items-center gap-3">
                <div class="text-xs font-black text-slate-200 uppercase tracking-[0.6em]">VS</div>
                <div class="px-4 py-2 bg-slate-50 rounded-2xl border border-slate-100 text-center">
                  <div class="text-[9px] font-black text-slate-400 uppercase mb-1">H2H</div>
                  <div class="text-xs font-black text-slate-900">{{ match.analysis.h2h.hWins }}-{{ match.analysis.h2h.draws }}-{{ match.analysis.h2h.aWins }}</div>
                </div>
              </div>

              <div class="flex-1 text-center space-y-4">
                <div class="relative w-24 h-24 mx-auto">
                  <div :class="[
                        'w-full h-full rounded-3xl flex items-center justify-center text-4xl font-black shadow-inner transition-all duration-500',
                        match.analysis.away.isBetterRank ? 'bg-indigo-50 text-indigo-600 border-4 border-indigo-200 animate-pulse-rank' : 'bg-slate-50 text-slate-900'
                      ]">
                    {{ match.away_team.charAt(0) }}
                  </div>
                  <div class="absolute -bottom-2 -right-2 bg-slate-900 text-white text-xs font-black px-3 py-1.5 rounded-xl shadow-xl">
                    #{{ match.analysis.away.rank || '?' }}
                  </div>
                </div>
                <div class="font-black text-slate-900 text-lg truncate">{{ match.away_team }}</div>
                <div class="flex flex-col gap-2">
                  <div class="flex justify-center gap-2">
                    <span class="text-[11px] font-black px-3 py-1 bg-emerald-100 text-emerald-600 rounded-lg">{{ Math.round(match.analysis.away.winRate) }}% V</span>
                    <span class="text-[11px] font-black px-3 py-1 bg-rose-100 text-rose-600 rounded-lg">{{ Math.round(match.analysis.away.lossRate) }}% L</span>
                  </div>
                  <div class="text-[10px] font-black text-slate-400 uppercase">
                    {{ match.analysis.away.wins }}V - {{ match.analysis.away.losses }}L |
                    <span :class="match.analysis.away.gd > 0 ? 'text-emerald-600' : 'text-rose-500'">{{ match.analysis.away.gd }} GD</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="bg-slate-50 rounded-2xl p-6 mb-8 border-l-8 border-indigo-600">
              <div class="text-[10px] font-black text-indigo-600 uppercase tracking-widest mb-2">Insight Neural-X</div>
              <p class="text-xs font-bold text-slate-600 leading-relaxed italic">"{{ match.analysis.why }}"</p>
            </div>

            <!-- More stats -->
            <button @click="toggleCard(match.id)"
                    class="w-full mb-8 px-6 py-4 bg-white rounded-2xl border border-slate-100 shadow-sm font-black text-sm text-slate-900 flex items-center justify-between hover:bg-slate-50 transition-all">
              <span>📊 More Stats</span>
              <span class="text-xs text-slate-400" :class="{ 'rotate-180': state.openCardId === match.id }">▼</span>
            </button>

            <div v-if="state.openCardId === match.id" class="mb-10 bg-white/60 rounded-2xl border border-white/80 p-6 space-y-5">
              <div class="grid grid-cols-3 gap-4">
                <div class="bg-slate-50 rounded-2xl p-4 border border-slate-100">
                  <div class="text-[10px] font-black text-slate-400 uppercase mb-2">Model Probs</div>
                  <div class="text-xs font-black text-slate-900 space-y-1">
                    <div>1: <span class="text-indigo-600">{{ Math.round(match.analysis.probs.h * 100) }}%</span></div>
                    <div>X: <span class="text-slate-600">{{ Math.round(match.analysis.probs.d * 100) }}%</span></div>
                    <div>2: <span class="text-rose-500">{{ Math.round(match.analysis.probs.a * 100) }}%</span></div>
                  </div>
                </div>

                <div class="bg-slate-50 rounded-2xl p-4 border border-slate-100">
                  <div class="text-[10px] font-black text-slate-400 uppercase mb-2">Implied</div>
                  <div class="text-xs font-black text-slate-900 space-y-1">
                    <div>1: <span class="text-indigo-600">{{ Math.round(match.analysis.implied.h * 100) }}%</span></div>
                    <div>X: <span class="text-slate-600">{{ Math.round(match.analysis.implied.d * 100) }}%</span></div>
                    <div>2: <span class="text-rose-500">{{ Math.round(match.analysis.implied.a * 100) }}%</span></div>
                  </div>
                </div>

                <div class="bg-slate-50 rounded-2xl p-4 border border-slate-100">
                  <div class="text-[10px] font-black text-slate-400 uppercase mb-2">Edges</div>
                  <div class="text-xs font-black text-slate-900 space-y-1">
                    <div>Pick Edge: <span :class="match.analysis.edge.pickEdge >= 0 ? 'text-emerald-600' : 'text-rose-500'">{{ (match.analysis.edge.pickEdge * 100).toFixed(1) }}pp</span></div>
                    <div>Best: <span :class="match.analysis.edge.bestEdge >= 0 ? 'text-emerald-600' : 'text-rose-500'">{{ (match.analysis.edge.bestEdge * 100).toFixed(1) }}pp</span> ({{ match.analysis.edge.bestMarket }})</div>
                    <div>H2H Avg Goals: <span class="text-slate-900">{{ match.analysis.h2h.avgGoals.toFixed(2) }}</span></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Odds & action -->
            <div class="flex items-center justify-between">
              <div class="flex gap-6">
                <div v-for="(odd, label) in { '1': match.home_odds, 'X': match.draw_odds, '2': match.away_odds }" :key="label" class="text-center">
                  <div class="text-[10px] font-black text-slate-300 uppercase">{{ label }}</div>
                  <div :class="['font-black text-lg', toNum(odd) >= 1.7 ? 'text-indigo-600 scale-110' : 'text-slate-900']">{{ odd || '—' }}</div>
                </div>
              </div>

              <a v-if="match.match_url" :href="match.match_url" target="_blank"
                 class="px-8 py-4 bg-slate-900 text-white rounded-2xl font-black hover:bg-indigo-600 transition-all shadow-lg transform hover:scale-105">
                DÉTAILS →
              </a>
            </div>

          </div>
        </div>

        <!-- Empty state -->
        <div v-else class="bg-white rounded-3xl py-64 text-center shadow-lg border border-slate-100">
          <div class="text-[120px] mb-12 grayscale opacity-10">🧠</div>
          <h2 class="text-6xl font-black text-slate-900 tracking-tighter">Aucun Match Neural-X</h2>
          <p class="text-slate-400 mt-6 max-w-lg mx-auto font-bold text-2xl">Ajustez vos filtres pour trouver les opportunités de la journée.</p>
        </div>

      </div>
    </div>
 
</template>

<style scoped>
.neural-card {
  opacity: 0;
  animation: neural-reveal 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
}

@keyframes neural-reveal {
  from { opacity: 0; transform: translateY(40px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes pulse-rank {
  0%, 100% { border-color: rgba(79, 70, 229, 0.1); box-shadow: 0 0 0 0 rgba(79, 70, 229, 0); }
  50% { border-color: rgba(79, 70, 229, 0.5); box-shadow: 0 0 30px 0 rgba(79, 70, 229, 0.1); }
}

.animate-pulse-rank {
  animation: pulse-rank 2.5s infinite ease-in-out;
}

.animate-slide-up {
  animation: slide-up 0.5s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
}

@keyframes slide-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Smooth show/hide for filter panel */
.fade-slide-enter-active, .fade-slide-leave-active {
  transition: all 220ms ease;
}
.fade-slide-enter-from, .fade-slide-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* Custom Range Slider */
input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none;
  height: 24px;
  width: 24px;
  border-radius: 8px;
  background: #4f46e5;
  cursor: pointer;
  border: 4px solid white;
  box-shadow: 0 6px 15px rgba(79, 70, 229, 0.3);
  margin-top: -8px;
}

input[type=range]::-webkit-slider-runnable-track {
  width: 100%;
  height: 8px;
  background: #ffffff;
  border-radius: 4px;
  border: 1px solid rgba(226, 232, 240, 0.8);
}
</style>
