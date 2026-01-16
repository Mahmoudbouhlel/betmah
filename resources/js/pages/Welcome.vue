<script setup lang="ts">
import AppLayout from '@/layouts/AppLayout.vue';
import { dashboard } from '@/routes';
import { type BreadcrumbItem } from '@/types';
import { Head } from '@inertiajs/vue3';
import { ref, computed, watch } from 'vue';

type Match = {
  id: number;
  match_key?: string;
  home_team: string;
  away_team: string;
  match_date?: string;
  match_time?: string;
  home_odds?: string;
  draw_odds?: string;
  away_odds?: string;
  match_url?: string;
  scraped_at?: string;
};

type H2H = {
  id: number;
  match_id: number;
  date?: string;
  home_team: string;
  away_team: string;
  score?: string;
  home_odds?: string;
  draw_odds?: string;
  away_odds?: string;
  created_at?: string;
};

type Standing = {
  id: number;
  match_id?: number;
  team: string;
  rank: string | number;
  mp?: string | number;
  wins?: string | number;
  draws?: string | number;
  losses?: string | number;
  goals?: string;
  gd?: string | number;
  pts?: string | number;
};

const props = defineProps<{
  matches: Match[];
  h2hMatches: H2H[];
  standings: Standing[];
}>();

const breadcrumbs: BreadcrumbItem[] = [
  { title: 'Dashboard', href: dashboard().url },
];

const minWinDiff = ref(0);
const minDrawDiff = ref(0);
const minLossDiff = ref(0);
const minConfidence = ref(0);

/* ------------------------- UTILS ------------------------- */
const toNum = (v: unknown, def = 0) => {
  const n = Number(String(v ?? '').trim().replace(',', '.'));
  return Number.isFinite(n) ? n : def;
};

const getTimeSafe = (t?: string) => {
  const s = String(t ?? '').trim();
  const m = s.match(/^(\d{2}):(\d{2})(?::(\d{2}))?$/);
  if (!m) return '00:00';
  return `${m[1]}:${m[2]}`;
};

const toDate = (d?: string) => {
  if (!d) return undefined;
  const dt = new Date(`${d}T00:00:00`);
  return isNaN(dt.getTime()) ? undefined : dt;
};

const fmtDateTime = (d?: string, t?: string) => {
  if (!d) return '';
  const dateTimeStr = `${d}T${t ?? '00:00'}`;
  const dt = new Date(dateTimeStr);
  if (isNaN(dt.getTime())) return d;
  return dt.toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

/* ------------------------- HELPERS ------------------------- */
const getTeamStanding = (team: string) =>
  props.standings.find(s => s.team.toLowerCase() === team.toLowerCase());

const getH2hForMatch = (matchId: number) =>
  props.h2hMatches.filter(h2h => h2h.match_id === matchId);

const parseScore = (score?: string): { h: number; a: number; ok: boolean } => {
  const s = String(score ?? '').trim();
  const m = s.match(/^\s*(\d+)\s*[:\-–]\s*(\d+)\s*/);
  if (!m) return { h: 0, a: 0, ok: false };
  const h = Number(m[1]);
  const a = Number(m[2]);
  return { h, a, ok: Number.isFinite(h) && Number.isFinite(a) };
};

const getH2hStats = (match: Match) => {
  const rows = getH2hForMatch(match.id);
  let homeWins = 0, awayWins = 0, draws = 0, total = 0;

  rows.forEach(r => {
    const { h, a, ok } = parseScore(r.score);
    if (!ok) return;
    total++;

    let currentHomeGoals: number, currentAwayGoals: number;

    if (r.home_team === match.home_team && r.away_team === match.away_team) {
      currentHomeGoals = h;
      currentAwayGoals = a;
    } else if (r.home_team === match.away_team && r.away_team === match.home_team) {
      currentHomeGoals = a;
      currentAwayGoals = h;
    } else {
      currentHomeGoals = h;
      currentAwayGoals = a;
    }

    if (currentHomeGoals > currentAwayGoals) homeWins++;
    else if (currentAwayGoals > currentHomeGoals) awayWins++;
    else draws++;
  });

  return { homeWins, awayWins, draws, total };
};

const getH2hPercentages = (s: { homeWins: number; awayWins: number; draws: number; total: number }) => {
  if (!s.total) return { pHome: 0, pDraw: 0, pAway: 0 };
  let pHome = Math.round((s.homeWins / s.total) * 100);
  let pAway = Math.round((s.awayWins / s.total) * 100);
  let pDraw = 100 - pHome - pAway;
  if (pDraw < 0) pDraw = 0;
  return { pHome, pDraw, pAway };
};

const hasH2hDominance = (match: Match, minDiff = 1) => {
  const stats = getH2hStats(match);
  return Math.abs(stats.homeWins - stats.awayWins) >= minDiff;
};

const isStrongFavoriteMatch = (match: Match) => {
  const home = getTeamStanding(match.home_team);
  const away = getTeamStanding(match.away_team);
  if (!home || !away) return false;

  const homeRank = toNum(home.rank, 9999);
  const awayRank = toNum(away.rank, 9999);
  const homeOdd = toNum(match.home_odds, 0);
  const awayOdd = toNum(match.away_odds, 0);
  if (homeOdd <= 2 || awayOdd <= 2) return false;

  const h2h = getH2hStats(match);
  const homeBetterH2h = h2h.homeWins > h2h.awayWins;
  const awayBetterH2h = h2h.awayWins > h2h.homeWins;

  if (homeBetterH2h && homeRank < awayRank && homeOdd < awayOdd) return true;
  if (awayBetterH2h && awayRank < homeRank && awayOdd < homeOdd) return true;

  return false;
};

const getOver25Probability = (match: Match) => {
  const rows = getH2hForMatch(match.id);
  // Only consider if there are at least 3 H2H matches
  if (rows.length < 3) return 0;

  // Count how many matches were over 2.5
  const over25 = rows.filter(r => {
    const { h, a, ok } = parseScore(r.score);
    return ok && (h + a) >= 3;
  });

  // If not all matches are over 2.5 → return 0
  if (over25.length !== rows.length) return 0;

  // Otherwise return percentage (which will always be 100%)
  return Math.round((over25.length / rows.length) * 100);
};


const isUnder25Match = (match: Match) => {
  const rows = getH2hForMatch(match.id);
  if (!rows.length) return false;
  return rows.every(r => {
    const { h, a, ok } = parseScore(r.score);
    return ok && (h + a) <= 2;
  });
};

const sortByDateTime = (a: Match, b: Match) => {
  const ad = toDate(a.match_date)?.getTime() ?? 0;
  const bd = toDate(b.match_date)?.getTime() ?? 0;
  if (ad !== bd) return ad - bd;
  return getTimeSafe(a.match_time).localeCompare(getTimeSafe(b.match_time));
};

/* ------------------------- STATE ------------------------- */
const currentPage = ref(1);
const perPage = ref(50);
const filterTop5 = ref(false);
const filterRankDiff = ref(0);
const searchTeam = ref("");
const filterH2hDominance = ref(false);
const minOver25Pct = ref(0);
const filterUnder25 = ref(false);
const filterStrongFavorite = ref(false);
const minMp = ref(0);

const today = new Date();
const yyyy = today.getFullYear();
const mm = String(today.getMonth() + 1).padStart(2, '0');
const dd = String(today.getDate()).padStart(2, '0');
const todayStr = `${yyyy}-${mm}-${dd}`;
const minDate = ref<string>(todayStr);
const maxDate = ref<string>(todayStr);

const minTime = ref('00:00');
const maxTime = ref('23:59');

watch([filterTop5, filterRankDiff, searchTeam, minDate, maxDate, minTime, maxTime, perPage, filterH2hDominance, minOver25Pct, minMp], () => {
  currentPage.value = 1;
});

/* ------------------------- PREDICTION ------------------------- */
const getPrediction = (match: Match) => {
  const home = getTeamStanding(match.home_team);
  const away = getTeamStanding(match.away_team);
  if (!home || !away)
    return { outcome: "X", label: "Unknown", confidence: 50 };

  let homeScore = 0, awayScore = 0;

  const homeRank = toNum(home.rank, 9999);
  const awayRank = toNum(away.rank, 9999);
  const homePts = toNum(home.pts, 0);
  const awayPts = toNum(away.pts, 0);

  const rankDiff = awayRank - homeRank;
  homeScore += Math.max(0, rankDiff) * 2;
  awayScore += Math.max(0, -rankDiff) * 2;

  const homePPM = home.mp ? homePts / toNum(home.mp, 1) : homePts;
  const awayPPM = away.mp ? awayPts / toNum(away.mp, 1) : awayPts;
  homeScore += homePPM * 3;
  awayScore += awayPPM * 3;

  const homeForm = (toNum(home.wins, 0) * 3 + toNum(home.draws, 0)) / (toNum(home.mp, 1) * 3);
  const awayForm = (toNum(away.wins, 0) * 3 + toNum(away.draws, 0)) / (toNum(away.mp, 1) * 3);
  homeScore += homeForm * 5;
  awayScore += awayForm * 5;

  const homeOdd = toNum(match.home_odds, 0);
  const awayOdd = toNum(match.away_odds, 0);
  if (homeOdd > 0 && awayOdd > 0) {
    const invHome = 1 / homeOdd, invAway = 1 / awayOdd;
    const total = invHome + invAway;
    homeScore += (invHome / total) * 10;
    awayScore += (invAway / total) * 10;
  }

  const h2hMatches = getH2hForMatch(match.id);
  h2hMatches.forEach(g => {
    const { h, a, ok } = parseScore(g.score);
    if (!ok) return;
    if (g.home_team === match.home_team) {
      if (h > a) homeScore += 0.8;
      else if (a > h) awayScore += 0.8;
    } else if (g.away_team === match.home_team) {
      if (a > h) homeScore += 0.8;
      else if (h > a) awayScore += 0.8;
    }
  });

  const winDiff = toNum(home.wins, 0) - toNum(away.wins, 0);
  homeScore += winDiff * 1.5;

  const drawDiff = toNum(home.draws, 0) - toNum(away.draws, 0);
  homeScore += drawDiff * 0.5;

  const lossDiff = toNum(away.losses, 0) - toNum(home.losses, 0);
  homeScore += lossDiff * 1.5;

  const total = homeScore + awayScore;
  if (total <= 0)
    return { outcome: "X", label: "Balanced", confidence: 50 };

  const homePct = Math.round((homeScore / total) * 100);
  const awayPct = 100 - homePct;

  if (Math.abs(homePct - awayPct) < 10)
    return { outcome: "X", label: "Draw Likely", confidence: 50 };

  return homePct > awayPct
    ? { outcome: "1", label: match.home_team, confidence: homePct }
    : { outcome: "2", label: match.away_team, confidence: awayPct };
};

/* ------------------------- FILTERING ------------------------- */
const chronological = computed(() => [...props.matches].sort(sortByDateTime));

const filteredMatches = computed(() =>
  chronological.value.filter(m => {
    const home = getTeamStanding(m.home_team);
    const away = getTeamStanding(m.away_team);
    if (!home || !away) return false;

    const dm = toDate(m.match_date)?.getTime() ?? 0;
    if (minDate.value && dm < (toDate(minDate.value)?.getTime() ?? -Infinity)) return false;
    if (maxDate.value && dm > (toDate(maxDate.value)?.getTime() ?? Infinity)) return false;
    const t = getTimeSafe(m.match_time);
    if (t < getTimeSafe(minTime.value) || t > getTimeSafe(maxTime.value)) return false;

    const diff = Math.abs(toNum(home.rank, 9999) - toNum(away.rank, 9999));
    if (filterTop5.value && toNum(home.rank, 9999) > 5 && toNum(away.rank, 9999) > 5) return false;
    if (filterRankDiff.value > 0 && diff < filterRankDiff.value) return false;

    if (minMp.value > 0) {
      const homeMp = toNum(home.mp, 0);
      const awayMp = toNum(away.mp, 0);
      if (homeMp < minMp.value || awayMp < minMp.value) return false;
    }

    if (searchTeam.value.trim()) {
      const s = searchTeam.value.toLowerCase();
      if (!m.home_team.toLowerCase().includes(s) && !m.away_team.toLowerCase().includes(s)) return false;
    }

    if (filterH2hDominance.value && !hasH2hDominance(m, 1)) return false;
    if (minOver25Pct.value > 0 && getOver25Probability(m) < minOver25Pct.value) return false;
    if (filterUnder25.value && !isUnder25Match(m)) return false;
    if (filterStrongFavorite.value && !isStrongFavoriteMatch(m)) return false;

    const prediction = getPrediction(m);
    if (minConfidence.value > 0 && prediction.confidence < minConfidence.value) return false;

    const winDiff = Math.abs(toNum(home.wins, 0) - toNum(away.wins, 0));
    if (minWinDiff.value > 0 && winDiff < minWinDiff.value) return false;

    const drawDiff = Math.abs(toNum(home.draws, 0) - toNum(away.draws, 0));
    if (minDrawDiff.value > 0 && drawDiff < minDrawDiff.value) return false;

    const lossDiff = Math.abs(toNum(home.losses, 0) - toNum(away.losses, 0));
    if (minLossDiff.value > 0 && lossDiff < minLossDiff.value) return false;

    return true;
  })
);

const totalMatches = computed(() => filteredMatches.value.length);
const totalPages = computed(() => Math.max(1, Math.ceil(totalMatches.value / perPage.value)));
const paginatedMatches = computed(() => {
  const start = (currentPage.value - 1) * perPage.value;
  return filteredMatches.value.slice(start, start + perPage.value);
});

const visiblePages = computed(() => {
  const maxPages = 5;
  let start = Math.max(1, currentPage.value - 2);
  let end = Math.min(totalPages.value, start + maxPages - 1);
  if (end - start < maxPages - 1) start = Math.max(1, end - maxPages + 1);
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
});

const goToPage = (p: number) => { if (p >= 1 && p <= totalPages.value) currentPage.value = p; };

const resetFilters = () => {
  filterTop5.value = false;
  filterRankDiff.value = 0;
  searchTeam.value = "";
  filterH2hDominance.value = false;
  filterUnder25.value = false;
  filterStrongFavorite.value = false;
  minOver25Pct.value = 0;
  minConfidence.value = 200;
  minMp.value = 0;
  minWinDiff.value = 0;
  minDrawDiff.value = 0;
  minLossDiff.value = 0;
  minTime.value = "00:00";
  maxTime.value = "23:59";
  minDate.value = todayStr;
  maxDate.value = todayStr;
  perPage.value = 50;
  currentPage.value = 1;
};
</script>

<template>
  <Head title="Football Dashboard" />
  <AppLayout :breadcrumbs="breadcrumbs">
    <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-slate-900 dark:to-indigo-900">

      <!-- Header -->
      <div class="relative overflow-hidden">
        <div class="absolute inset-0 bg-gradient-to-r from-blue-600/10 to-purple-600/10 dark:from-blue-400/5 dark:to-purple-400/5"></div>
        <div class="relative px-6 py-8">
          <div class="max-w-7xl mx-auto">
            <h1 class="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              ⚽ Football Analytics
            </h1>
            <p class="text-gray-600 dark:text-gray-400 mt-2 text-lg">Smart predictions and insights</p>
          </div>
        </div>
      </div>

      <div class="max-w-7xl mx-auto px-6 pb-12">

        <!-- Modern Filter Panel -->
        <div class="bg-white/80 dark:bg-gray-800/80 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/20 dark:border-gray-700/20 p-6 mb-8 -mt-4 relative z-10">
          <div class="flex flex-wrap gap-4 items-center">

            <!-- Date Range -->
            <div class="flex items-center gap-3 bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-xl p-3">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">📅</span>
              <input type="date" v-model="minDate"
                class="bg-transparent border-0 text-sm focus:ring-2 focus:ring-blue-500 rounded-lg dark:text-white">
              <span class="text-gray-400">→</span>
              <input type="date" v-model="maxDate"
                class="bg-transparent border-0 text-sm focus:ring-2 focus:ring-blue-500 rounded-lg dark:text-white">
            </div>

            <!-- Time Range -->
            <div class="flex items-center gap-3 bg-gradient-to-r from-emerald-500/10 to-teal-500/10 rounded-xl p-3">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">⏰</span>
              <input type="time" v-model="minTime"
                class="bg-transparent border-0 text-sm focus:ring-2 focus:ring-emerald-500 rounded-lg dark:text-white">
              <span class="text-gray-400">→</span>
              <input type="time" v-model="maxTime"
                class="bg-transparent border-0 text-sm focus:ring-2 focus:ring-emerald-500 rounded-lg dark:text-white">
            </div>

            <!-- Toggle Filters -->
            <button @click="filterTop5 = !filterTop5"
              class="group flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 text-sm font-medium"
              :class="filterTop5
                ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg transform scale-105'
                : 'bg-gray-100/80 dark:bg-gray-700/80 text-gray-600 dark:text-gray-300 hover:bg-gray-200/80 dark:hover:bg-gray-600/80'">
              <span class="transition-transform duration-300" :class="filterTop5 ? 'rotate-12' : ''">🏆</span>
              Top 5 Teams
            </button>

            <button @click="filterH2hDominance = !filterH2hDominance"
              class="group flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 text-sm font-medium"
              :class="filterH2hDominance
                ? 'bg-gradient-to-r from-purple-500 to-purple-600 text-white shadow-lg transform scale-105'
                : 'bg-gray-100/80 dark:bg-gray-700/80 text-gray-600 dark:text-gray-300 hover:bg-gray-200/80 dark:hover:bg-gray-600/80'">
              <span class="transition-transform duration-300" :class="filterH2hDominance ? 'rotate-12' : ''">⚔️</span>
              H2H Dominance
            </button>

            <button @click="filterUnder25 = !filterUnder25"
              class="group flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 text-sm font-medium"
              :class="filterUnder25
                ? 'bg-gradient-to-r from-amber-500 to-amber-600 text-white shadow-lg transform scale-105'
                : 'bg-gray-100/80 dark:bg-gray-700/80 text-gray-600 dark:text-gray-300 hover:bg-gray-200/80 dark:hover:bg-gray-600/80'">
              <span class="transition-transform duration-300" :class="filterUnder25 ? 'rotate-12' : ''">🔽</span>
              Under 2.5
            </button>

            <button @click="filterStrongFavorite = !filterStrongFavorite"
              class="group flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 text-sm font-medium"
              :class="filterStrongFavorite
                ? 'bg-gradient-to-r from-emerald-500 to-emerald-600 text-white shadow-lg transform scale-105'
                : 'bg-gray-100/80 dark:bg-gray-700/80 text-gray-600 dark:text-gray-300 hover:bg-gray-200/80 dark:hover:bg-gray-600/80'">
              <span class="transition-transform duration-300" :class="filterStrongFavorite ? 'rotate-12' : ''">💪</span>
              Strong Favorite
            </button>
          </div>

          <!-- Slider Filters -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-6 pt-6 border-t border-gray-200/50 dark:border-gray-600/50">

            <!-- Rank Diff Slider -->
            <div class="space-y-2">
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                📊 Min Rank Diff: <span class="px-2 py-1 bg-blue-500/20 text-blue-700 dark:text-blue-300 rounded-full text-xs font-bold">{{ filterRankDiff }}</span>
              </label>
              <input type="range" min="0" max="20" v-model.number="filterRankDiff"
                class="w-full h-2 bg-gradient-to-r from-blue-200 to-blue-400 rounded-full appearance-none cursor-pointer slider-thumb-blue">
            </div>

            <!-- Min MP Slider -->
            <div class="space-y-2">
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                🏃 Min MP: <span class="px-2 py-1 bg-green-500/20 text-green-700 dark:text-green-300 rounded-full text-xs font-bold">{{ minMp }}</span>
              </label>
              <input type="range" min="0" max="38" v-model.number="minMp"
                class="w-full h-2 bg-gradient-to-r from-green-200 to-green-400 rounded-full appearance-none cursor-pointer slider-thumb-green">
            </div>

            <!-- Over 2.5% Slider -->
            <div class="space-y-2">
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                ⚽ Min Over 2.5%: <span class="px-2 py-1 bg-purple-500/20 text-purple-700 dark:text-purple-300 rounded-full text-xs font-bold">{{ minOver25Pct }}%</span>
              </label>
              <input type="range" min="0" max="100" step="5" v-model.number="minOver25Pct"
                class="w-full h-2 bg-gradient-to-r from-purple-200 to-purple-400 rounded-full appearance-none cursor-pointer slider-thumb-purple">
            </div>

            <!-- Confidence Slider -->
            <div class="space-y-2">
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                🎯 Min Confidence: <span class="px-2 py-1 bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 rounded-full text-xs font-bold">{{ minConfidence }}%</span>
              </label>
              <input type="range" min="0" max="100" step="5" v-model.number="minConfidence"
                class="w-full h-2 bg-gradient-to-r from-indigo-200 to-indigo-400 rounded-full appearance-none cursor-pointer slider-thumb-indigo">
            </div>

            <!-- W/D/L Diff Sliders -->
            <div class="space-y-2">
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                ✅ Min Win Diff: <span class="px-2 py-1 bg-green-500/20 text-green-700 dark:text-green-300 rounded-full text-xs font-bold">{{ minWinDiff }}</span>
              </label>
              <input type="range" min="0" max="20" v-model.number="minWinDiff"
                class="w-full h-2 bg-gradient-to-r from-green-200 to-green-400 rounded-full appearance-none cursor-pointer slider-thumb-green">
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                ➖ Min Draw Diff: <span class="px-2 py-1 bg-blue-500/20 text-blue-700 dark:text-blue-300 rounded-full text-xs font-bold">{{ minDrawDiff }}</span>
              </label>
              <input type="range" min="0" max="20" v-model.number="minDrawDiff"
                class="w-full h-2 bg-gradient-to-r from-blue-200 to-blue-400 rounded-full appearance-none cursor-pointer slider-thumb-blue">
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                ❌ Min Loss Diff: <span class="px-2 py-1 bg-red-500/20 text-red-700 dark:text-red-300 rounded-full text-xs font-bold">{{ minLossDiff }}</span>
              </label>
              <input type="range" min="0" max="20" v-model.number="minLossDiff"
                class="w-full h-2 bg-gradient-to-r from-red-200 to-red-400 rounded-full appearance-none cursor-pointer slider-thumb-red">
            </div>

            <!-- Search Box -->
            <div class="space-y-2">
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                🔍 Search Team
              </label>
              <div class="relative">
                <input type="text" placeholder="Enter team name..." v-model="searchTeam"
                  class="w-full px-4 py-2 bg-white/50 dark:bg-gray-700/50 border border-gray-200/50 dark:border-gray-600/50 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm">
                <svg v-if="!searchTeam" class="w-4 h-4 absolute right-3 top-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M17 10.5A6.5 6.5 0 104 10.5a6.5 6.5 0 0013 0z" />
                </svg>
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="flex justify-between items-center mt-6 pt-6 border-t border-gray-200/50 dark:border-gray-600/50">
            <div class="flex items-center gap-4">
              <span class="text-sm text-gray-600 dark:text-gray-400">
                Showing <span class="font-bold text-blue-600 dark:text-blue-400">{{ paginatedMatches.length }}</span> of
                <span class="font-bold text-purple-600 dark:text-purple-400">{{ totalMatches }}</span> matches
              </span>
              <select v-model.number="perPage"
                class="px-3 py-1 bg-white/50 dark:bg-gray-700/50 border border-gray-200/50 dark:border-gray-600/50 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 backdrop-blur-sm">
                <option :value="12">12 per page</option>
                <option :value="24">24 per page</option>
                <option :value="50">50 per page</option>
                <option :value="100">100 per page</option>
              </select>
            </div>

            <button @click="resetFilters"
              class="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-gray-500 to-gray-600 text-white rounded-xl hover:from-gray-600 hover:to-gray-700 transition-all duration-300 transform hover:scale-105 shadow-lg">
              <span class="text-lg">🔄</span>
              Reset All
            </button>
          </div>
        </div>

        <!-- Match Cards Grid -->
        <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div v-for="match in paginatedMatches" :key="match.id"
               class="group relative bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/20 dark:border-gray-700/20 p-6 hover:shadow-2xl hover:-translate-y-2 transition-all duration-500 overflow-hidden">

            <!-- Gradient Overlay -->
            <div class="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

            <!-- Content -->
            <div class="relative z-10">

              <!-- Header -->
              <div class="flex justify-between items-start mb-4">
                <div class="flex items-center gap-2 px-3 py-1 bg-blue-500/10 rounded-full">
                  <span class="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                  <span class="text-xs font-medium text-blue-700 dark:text-blue-300">
                    {{ fmtDateTime(match.match_date, match.match_time) }}
                  </span>
                </div>
                <div v-if="match.scraped_at" class="text-xs text-gray-500 bg-gray-100/50 dark:bg-gray-700/50 px-2 py-1 rounded-full">
                  Updated {{ new Date(match.scraped_at).toLocaleTimeString() }}
                </div>
              </div>

              <!-- Teams -->
        <div class="text-center mb-6">
  <div class="flex items-center justify-center gap-6 mb-3">

    <!-- Home Team -->
    <div class="flex-1 text-right">
      <h3 class="font-bold text-xl text-gray-900 dark:text-gray-100 truncate">
        {{ match.home_team }}
      </h3>
      <div
        v-if="getTeamStanding(match.home_team)"
        class="inline-flex items-center gap-2 mt-2 px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-xs font-medium text-gray-700 dark:text-gray-300"
      >
        <span class="text-indigo-600 dark:text-indigo-400 font-bold">
          #{{ getTeamStanding(match.home_team)?.rank }}
        </span>
        <span>•</span>
        <span>{{ getTeamStanding(match.home_team)?.pts }} pts</span>
      </div>
    </div>

    <!-- VS Badge -->
    <div class="px-5 py-2 bg-gradient-to-r from-indigo-100 to-indigo-200 dark:from-indigo-700 dark:to-indigo-600 rounded-full shadow">
      <span class="text-indigo-800 dark:text-indigo-200 font-extrabold tracking-wide">VS</span>
    </div>

    <!-- Away Team -->
    <div class="flex-1 text-left">
      <h3 class="font-bold text-xl text-gray-900 dark:text-gray-100 truncate">
        {{ match.away_team }}
      </h3>
      <div
        v-if="getTeamStanding(match.away_team)"
        class="inline-flex items-center gap-2 mt-2 px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-xs font-medium text-gray-700 dark:text-gray-300"
      >
        <span class="text-indigo-600 dark:text-indigo-400 font-bold">
          #{{ getTeamStanding(match.away_team)?.rank }}
        </span>
        <span>•</span>
        <span>{{ getTeamStanding(match.away_team)?.pts }} pts</span>
      </div>
    </div>

  </div>
</div>


              <!-- Prediction -->
              <div class="mb-6">
                <div class="flex items-center justify-center gap-2 mb-3">
                  <span class="px-4 py-2 rounded-full text-sm font-bold shadow-lg"
                        :class="{
                          'bg-gradient-to-r from-green-500 to-emerald-500 text-white': getPrediction(match).outcome === '1',
                          'bg-gradient-to-r from-gray-400 to-gray-500 text-white': getPrediction(match).outcome === 'X',
                          'bg-gradient-to-r from-red-500 to-rose-500 text-white': getPrediction(match).outcome === '2'
                        }">
                    🤖 {{ getPrediction(match).outcome }} - {{ getPrediction(match).label }}
                  </span>
                </div>

                <!-- Confidence Bar -->
                <div class="relative">
                  <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div class="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 transition-all duration-1000 ease-out"
                         :style="{ width: getPrediction(match).confidence + '%' }">
                    </div>
                  </div>
                  <div class="flex justify-between mt-1">
                    <span class="text-xs text-gray-500">Confidence</span>
                    <span class="text-xs font-bold"
                          :class="getPrediction(match).confidence > 70 ? 'text-green-600' : getPrediction(match).confidence > 50 ? 'text-yellow-600' : 'text-red-600'">
                      {{ getPrediction(match).confidence }}%
                    </span>
                  </div>
                </div>
              </div>

              <!-- Odds -->
              <div class="grid grid-cols-3 gap-2 mb-6">
                <div class="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 border border-green-200 dark:border-green-700 rounded-xl p-3 text-center">
                  <div class="text-xs text-green-600 dark:text-green-400 font-medium mb-1">Home</div>
                  <div class="font-bold text-green-700 dark:text-green-300">{{ match.home_odds ?? '--' }}</div>
                </div>
                <div class="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-700/20 dark:to-gray-600/20 border border-gray-200 dark:border-gray-600 rounded-xl p-3 text-center">
                  <div class="text-xs text-gray-600 dark:text-gray-400 font-medium mb-1">Draw</div>
                  <div class="font-bold text-gray-700 dark:text-gray-300">{{ match.draw_odds ?? '--' }}</div>
                </div>
                <div class="bg-gradient-to-br from-red-50 to-red-100 dark:from-red-900/20 dark:to-red-800/20 border border-red-200 dark:border-red-700 rounded-xl p-3 text-center">
                  <div class="text-xs text-red-600 dark:text-red-400 font-medium mb-1">Away</div>
                  <div class="font-bold text-red-700 dark:text-red-300">{{ match.away_odds ?? '--' }}</div>
                </div>
              </div>

              <!-- Quick Stats -->
              <div class="flex justify-center gap-4 mb-6 text-xs">
                <span v-if="hasH2hDominance(match)"
                  class="flex items-center gap-1 px-2 py-1 bg-purple-500/20 text-purple-700 dark:text-purple-300 rounded-full">
                  ⚔️ H2H Dominance
                </span>
                <span class="flex items-center gap-1 px-2 py-1 bg-blue-500/20 text-blue-700 dark:text-blue-300 rounded-full">
                  ⚽ Over 2.5: {{ getOver25Probability(match) }}%
                </span>
              </div>

              <!-- Team Stats Grid -->
              <div class="grid grid-cols-2 gap-4 mb-6">
                <!-- Home Team Stats -->
                <div v-if="getTeamStanding(match.home_team)"
                     class="bg-gradient-to-br from-blue-50/50 to-indigo-50/50 dark:from-blue-900/10 dark:to-indigo-900/10 rounded-xl p-3 border border-blue-200/30 dark:border-blue-700/30">
                  <div class="text-xs text-blue-600 dark:text-blue-400 font-medium mb-2 uppercase tracking-wide">Home Form</div>
                  <div class="space-y-1 text-xs">
                    <div class="flex justify-between">
                      <span>MP:</span>
                      <span class="font-bold">{{ getTeamStanding(match.home_team)?.mp ?? 0 }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span>W-D-L:</span>
                      <span class="font-bold">{{ getTeamStanding(match.home_team)?.wins ?? 0 }}-{{ getTeamStanding(match.home_team)?.draws ?? 0 }}-{{ getTeamStanding(match.home_team)?.losses ?? 0 }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span>GF/GA:</span>
                      <span class="font-bold">{{ getTeamStanding(match.home_team)?.goals ?? '-' }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span>GD:</span>
                      <span class="font-bold"
                            :class="{
                              'text-green-600': toNum(getTeamStanding(match.home_team)?.gd, 0) > 0,
                              'text-red-600': toNum(getTeamStanding(match.home_team)?.gd, 0) < 0,
                              'text-gray-600': toNum(getTeamStanding(match.home_team)?.gd, 0) === 0
                            }">
                        {{ getTeamStanding(match.home_team)?.gd ?? 0 }}
                      </span>
                    </div>
                    <div class="flex justify-between border-t border-blue-200/50 dark:border-blue-700/50 pt-1">
                      <span>Points:</span>
                      <span class="font-bold text-blue-700 dark:text-blue-300">{{ getTeamStanding(match.home_team)?.pts ?? 0 }}</span>
                    </div>
                  </div>
                </div>

                <!-- Away Team Stats -->
                <div v-if="getTeamStanding(match.away_team)"
                     class="bg-gradient-to-br from-red-50/50 to-rose-50/50 dark:from-red-900/10 dark:to-rose-900/10 rounded-xl p-3 border border-red-200/30 dark:border-red-700/30">
                  <div class="text-xs text-red-600 dark:text-red-400 font-medium mb-2 uppercase tracking-wide">Away Form</div>
                  <div class="space-y-1 text-xs">
                    <div class="flex justify-between">
                      <span>MP:</span>
                      <span class="font-bold">{{ getTeamStanding(match.away_team)?.mp ?? 0 }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span>W-D-L:</span>
                      <span class="font-bold">{{ getTeamStanding(match.away_team)?.wins ?? 0 }}-{{ getTeamStanding(match.away_team)?.draws ?? 0 }}-{{ getTeamStanding(match.away_team)?.losses ?? 0 }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span>GF/GA:</span>
                      <span class="font-bold">{{ getTeamStanding(match.away_team)?.goals ?? '-' }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span>GD:</span>
                      <span class="font-bold"
                            :class="{
                              'text-green-600': toNum(getTeamStanding(match.away_team)?.gd, 0) > 0,
                              'text-red-600': toNum(getTeamStanding(match.away_team)?.gd, 0) < 0,
                              'text-gray-600': toNum(getTeamStanding(match.away_team)?.gd, 0) === 0
                            }">
                        {{ getTeamStanding(match.away_team)?.gd ?? 0 }}
                      </span>
                    </div>
                    <div class="flex justify-between border-t border-red-200/50 dark:border-red-700/50 pt-1">
                      <span>Points:</span>
                      <span class="font-bold text-red-700 dark:text-red-300">{{ getTeamStanding(match.away_team)?.pts ?? 0 }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- H2H Section -->
              <div v-if="getH2hForMatch(match.id).length" class="mb-4">
                <div class="bg-gradient-to-r from-purple-50/50 to-pink-50/50 dark:from-purple-900/10 dark:to-pink-900/10 rounded-xl p-4 border border-purple-200/30 dark:border-purple-700/30">
                  <div class="flex items-center gap-2 mb-3">
                    <span class="text-sm font-medium text-purple-700 dark:text-purple-300">⚔️ Head to Head</span>
                  </div>

                  <!-- H2H Stats -->
                  <div class="grid grid-cols-3 gap-2 mb-3 text-xs">
                    <div class="text-center">
                      <div class="w-8 h-8 mx-auto bg-green-500 rounded-full flex items-center justify-center text-white font-bold text-xs mb-1">
                        {{ getH2hStats(match).homeWins }}
                      </div>
                      <div class="text-green-600 dark:text-green-400 font-medium">{{ match.home_team.slice(0, 8) }}</div>
                    </div>
                    <div class="text-center">
                      <div class="w-8 h-8 mx-auto bg-gray-400 rounded-full flex items-center justify-center text-white font-bold text-xs mb-1">
                        {{ getH2hStats(match).draws }}
                      </div>
                      <div class="text-gray-600 dark:text-gray-400 font-medium">Draws</div>
                    </div>
                    <div class="text-center">
                      <div class="w-8 h-8 mx-auto bg-red-500 rounded-full flex items-center justify-center text-white font-bold text-xs mb-1">
                        {{ getH2hStats(match).awayWins }}
                      </div>
                      <div class="text-red-600 dark:text-red-400 font-medium">{{ match.away_team.slice(0, 8) }}</div>
                    </div>
                  </div>

                  <!-- H2H Progress Bar -->
                  <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mb-3">
                    <div class="h-full flex">
                      <div class="bg-green-500 transition-all duration-1000" :style="{ width: getH2hPercentages(getH2hStats(match)).pHome + '%' }"></div>
                      <div class="bg-gray-400 transition-all duration-1000" :style="{ width: getH2hPercentages(getH2hStats(match)).pDraw + '%' }"></div>
                      <div class="bg-red-500 transition-all duration-1000" :style="{ width: getH2hPercentages(getH2hStats(match)).pAway + '%' }"></div>
                    </div>
                  </div>

                  <!-- Recent Matches -->
                  <div class="space-y-1">
                    <div class="text-xs text-purple-600 dark:text-purple-400 font-medium mb-2">Recent Matches:</div>
                    <div v-for="h2h in getH2hForMatch(match.id).slice(0, 3)" :key="h2h.id"
                         class="flex justify-between items-center text-xs bg-white/50 dark:bg-gray-800/50 rounded-lg p-2">
                      <span class="truncate">{{ h2h.home_team }} vs {{ h2h.away_team }}</span>
                      <span class="font-bold text-purple-600 dark:text-purple-300">{{ h2h.score }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Footer -->
              <div class="flex justify-between items-center pt-4 border-t border-gray-200/50 dark:border-gray-600/50">
                <a :href="match.match_url" target="_blank"
                   class="flex items-center gap-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 text-sm transition-colors">
                  <span>View Details</span>
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
                <div v-if="match.match_key" class="text-xs text-gray-500 truncate max-w-[40%]">
                  ID: {{ match.match_key }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Modern Pagination -->
        <div v-if="totalPages > 1" class="flex justify-center items-center gap-2 mt-12">
          <button :disabled="currentPage === 1" @click="goToPage(currentPage - 1)"
                  class="flex items-center justify-center w-10 h-10 rounded-xl bg-white/80 dark:bg-gray-800/80 backdrop-blur-xl shadow-lg border border-white/20 dark:border-gray-700/20 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed hover:scale-105">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          <span v-if="visiblePages[0] > 1" class="text-gray-400 dark:text-gray-500 mx-2">...</span>

          <button v-for="page in visiblePages" :key="page"
                  @click="goToPage(page)"
                  class="flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-300 font-medium text-sm hover:scale-105"
                  :class="page === currentPage
                    ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg transform scale-105'
                    : 'bg-white/80 dark:bg-gray-800/80 backdrop-blur-xl shadow-lg border border-white/20 dark:border-gray-700/20 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400'">
            {{ page }}
          </button>

          <span v-if="visiblePages[visiblePages.length - 1] < totalPages" class="text-gray-400 dark:text-gray-500 mx-2">...</span>

          <button :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)"
                  class="flex items-center justify-center w-10 h-10 rounded-xl bg-white/80 dark:bg-gray-800/80 backdrop-blur-xl shadow-lg border border-white/20 dark:border-gray-700/20 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed hover:scale-105">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style>
/* Custom slider styles */
.slider-thumb-blue::-webkit-slider-thumb {
  appearance: none;
  height: 16px;
  width: 16px;
  border-radius: 50%;
  background: linear-gradient(45deg, #3B82F6, #1E40AF);
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(59, 130, 246, 0.4);
}

.slider-thumb-green::-webkit-slider-thumb {
  appearance: none;
  height: 16px;
  width: 16px;
  border-radius: 50%;
  background: linear-gradient(45deg, #10B981, #047857);
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.4);
}

.slider-thumb-purple::-webkit-slider-thumb {
  appearance: none;
  height: 16px;
  width: 16px;
  border-radius: 50%;
  background: linear-gradient(45deg, #8B5CF6, #5B21B6);
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(139, 92, 246, 0.4);
}

.slider-thumb-indigo::-webkit-slider-thumb {
  appearance: none;
  height: 16px;
  width: 16px;
  border-radius: 50%;
  background: linear-gradient(45deg, #6366F1, #4338CA);
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.4);
}

.slider-thumb-red::-webkit-slider-thumb {
  appearance: none;
  height: 16px;
  width: 16px;
  border-radius: 50%;
  background: linear-gradient(45deg, #EF4444, #DC2626);
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.4);
}

/* Smooth animations */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.group {
  animation: fadeInUp 0.6s ease-out forwards;
}
</style>
