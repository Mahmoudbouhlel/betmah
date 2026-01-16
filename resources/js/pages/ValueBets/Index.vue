<script setup lang="ts">
import AppLayout from '@/layouts/AppLayout.vue';
import { dashboard } from '@/routes';
import { type BreadcrumbItem } from '@/types';
import { Head } from '@inertiajs/vue3';
import { ref, computed } from 'vue';

type H2HMatch = {
  date: string;
  home_team: string;
  away_team: string;
  score: string;
  home_odds?: string;
  draw_odds?: string;
  away_odds?: string;
};

type ValueBet = {
  id: number;
  type?: string;
  home_team: string;
  away_team: string;
  match_date: string;
  match_time: string;
  match_url?: string;
  home_odds: string;
  away_odds: string;
  home_rank: string | number;
  away_rank: string | number;
  home_mp?: string | number;
  home_wins?: string | number;
  home_draws?: string | number;
  home_losses?: string | number;
  home_pts?: string | number;
  home_gd?: string | number;
  away_mp?: string | number;
  away_wins?: string | number;
  away_draws?: string | number;
  away_losses?: string | number;
  away_pts?: string | number;
  away_gd?: string | number;
  home_wins_vs_away: number;
  away_wins_vs_home: number;
  h2h_history?: H2HMatch[];
};

const props = defineProps<{ valueBets: ValueBet[] }>();

const breadcrumbs: BreadcrumbItem[] = [
  { title: 'Dashboard', href: dashboard().url },
  { title: 'Value Bets', href: '/value-bets' },
];

/* ------------------------- ENHANCED PREDICTION ALGORITHM ------------------------- */
const calcH2hPct = (home: number, away: number) => {
  const total = home + away;
  if (total === 0) return { pHome: 50, pAway: 50 };
  return {
    pHome: Math.round((home / total) * 100),
    pAway: Math.round((away / total) * 100),
  };
};

// Enhanced prediction with multiple factors
const predictWinner = (bet: ValueBet) => {
  const { pHome, pAway } = calcH2hPct(bet.home_wins_vs_away, bet.away_wins_vs_home);

  // Form calculation (recent performance)
  const homeWins = Number(bet.home_wins) || 0;
  const homeDraws = Number(bet.home_draws) || 0;
  const homeLosses = Number(bet.home_losses) || 0;
  const homeGD = Number(bet.home_gd) || 0;
  const homePts = Number(bet.home_pts) || 0;
  const homeMP = Number(bet.home_mp) || 1;

  const awayWins = Number(bet.away_wins) || 0;
  const awayDraws = Number(bet.away_draws) || 0;
  const awayLosses = Number(bet.away_losses) || 0;
  const awayGD = Number(bet.away_gd) || 0;
  const awayPts = Number(bet.away_pts) || 0;
  const awayMP = Number(bet.away_mp) || 1;

  // Points per game ratio
  const homePPG = homePts / homeMP;
  const awayPPG = awayPts / awayMP;

  // Win ratio
  const homeWinRate = (homeWins / homeMP) * 100;
  const awayWinRate = (awayWins / awayMP) * 100;

  // Form score with multiple factors
  const homeFormScore = (homePPG * 20) + (homeWinRate * 0.8) + (homeGD * 0.3);
  const awayFormScore = (awayPPG * 20) + (awayWinRate * 0.8) + (awayGD * 0.3);

  // Rank advantage (lower rank is better)
  const homeRank = Number(bet.home_rank) || 999;
  const awayRank = Number(bet.away_rank) || 999;
  const rankAdvantage = awayRank - homeRank; // Positive means home has better rank

  // Combined strength calculation
  const homeStrength = homeFormScore * 0.6 + pHome * 0.25 + (rankAdvantage > 0 ? rankAdvantage * 2 : 0) * 0.15;
  const awayStrength = awayFormScore * 0.6 + pAway * 0.25 + (rankAdvantage < 0 ? Math.abs(rankAdvantage) * 2 : 0) * 0.15;

  const strengthDiff = Math.abs(homeStrength - awayStrength);
  const total = homeStrength + awayStrength || 1;
  const confidence = Math.min(95, Math.round((Math.max(homeStrength, awayStrength) / total) * 100));

  let winner: string | "draw" = "draw";
  let prediction_type = "balanced";

  if (strengthDiff <= 3) {
    winner = "draw";
    prediction_type = "draw";
  } else if (homeStrength > awayStrength) {
    winner = bet.home_team;
    prediction_type = "home";
  } else {
    winner = bet.away_team;
    prediction_type = "away";
  }

  // Determine strength level
  let strengthLevel = "weak";
  if (confidence >= 80) strengthLevel = "very_strong";
  else if (confidence >= 70) strengthLevel = "strong";
  else if (confidence >= 60) strengthLevel = "moderate";

  return {
    winner,
    confidence,
    isStrong: confidence >= 70,
    prediction_type,
    strengthLevel,
    homeFormScore: Math.round(homeFormScore),
    awayFormScore: Math.round(awayFormScore),
    homePPG: homePPG.toFixed(1),
    awayPPG: awayPPG.toFixed(1),
    homeWinRate: homeWinRate.toFixed(0),
    awayWinRate: awayWinRate.toFixed(0)
  };
};

const formatDate = (date: string, time: string) =>
  new Date(`${date}T${time}`).toLocaleString("en-US", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

/* ------------------------- FILTERS ------------------------- */
const currentPage = ref(1);
const perPage = ref(24);
const searchTeam = ref("");
const showOnlyStrong = ref(false);
const minMP = ref(0);
const strengthFilter = ref<"all" | "very_strong" | "strong" | "moderate" | "weak">("all");
const predictionFilter = ref<"all" | "home" | "away" | "draw">("all");
const winFilter = ref<"all" | "high_wins" | "low_wins">("all");
const rankFilter = ref<"all" | "top_ranked" | "mid_ranked" | "low_ranked">("all");
const h2hFilter = ref<"all" | "many_h2h" | "few_h2h">("all");

// Date range defaults (today)
const today = new Date().toISOString().split("T")[0];
const dateFrom = ref(today);
const dateTo = ref(today);
const timeFrom = ref("00:00");
const timeTo = ref("23:59");

const filteredBets = computed(() =>
  props.valueBets.filter((b) => {
    const s = searchTeam.value.toLowerCase();
    const prediction = predictWinner(b);
    const homeMP = Number(b.home_mp) || 0;
    const awayMP = Number(b.away_mp) || 0;
    const homeWins = Number(b.home_wins) || 0;
    const awayWins = Number(b.away_wins) || 0;
    const homeRank = Number(b.home_rank) || 999;
    const awayRank = Number(b.away_rank) || 999;
    const h2hCount = b.h2h_history?.length || 0;

    const matchDateTime = new Date(`${b.match_date}T${b.match_time}`);
    const start = new Date(`${dateFrom.value}T${timeFrom.value}`);
    const end = new Date(`${dateTo.value}T${timeTo.value}`);

    if (matchDateTime < start || matchDateTime > end) return false;
    if (s && !b.home_team.toLowerCase().includes(s) && !b.away_team.toLowerCase().includes(s)) return false;
    if (homeMP < minMP.value || awayMP < minMP.value) return false;
    if (showOnlyStrong.value && !prediction.isStrong) return false;

    // Strength filter
    if (strengthFilter.value !== "all" && prediction.strengthLevel !== strengthFilter.value) return false;

    // Win filter
    if (winFilter.value !== "all") {
      if (winFilter.value === "high_wins" && (homeWins < 5 || awayWins < 5)) return false;
      if (winFilter.value === "low_wins" && (homeWins >= 5 || awayWins >= 5)) return false;
    }

    // Rank filter
    if (rankFilter.value !== "all") {
      const avgRank = (homeRank + awayRank) / 2;
      if (rankFilter.value === "top_ranked" && avgRank > 3) return false;
      if (rankFilter.value === "mid_ranked" && (avgRank <= 3 || avgRank > 8)) return false;
      if (rankFilter.value === "low_ranked" && avgRank <= 8) return false;
    }

    // H2H filter
    if (h2hFilter.value !== "all") {
      if (h2hFilter.value === "many_h2h" && h2hCount < 4) return false;
      if (h2hFilter.value === "few_h2h" && h2hCount >= 4) return false;
    }

    // Prediction outcome filter
    if (predictionFilter.value !== "all") {
      if (predictionFilter.value === "home" && prediction.winner !== b.home_team) return false;
      if (predictionFilter.value === "away" && prediction.winner !== b.away_team) return false;
      if (predictionFilter.value === "draw" && prediction.winner !== "draw") return false;
    }

    return true;
  })
);

const totalBets = computed(() => filteredBets.value.length);
const totalPages = computed(() => Math.max(1, Math.ceil(totalBets.value / perPage.value)));
const paginatedBets = computed(() => {
  const start = (currentPage.value - 1) * perPage.value;
  return filteredBets.value.slice(start, start + perPage.value);
});

const visiblePages = computed(() => {
  const maxPages = 7;
  let start = Math.max(1, currentPage.value - 3);
  let end = Math.min(totalPages.value, start + maxPages - 1);
  if (end - start < maxPages - 1) start = Math.max(1, end - maxPages + 1);
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
});

const goToPage = (p: number) => {
  if (p >= 1 && p <= totalPages.value) currentPage.value = p;
};

const resetFilters = () => {
  searchTeam.value = "";
  showOnlyStrong.value = false;
  minMP.value = 0;
  strengthFilter.value = "all";
  winFilter.value = "all";
  predictionFilter.value = "all";
  rankFilter.value = "all";
  h2hFilter.value = "all";
  dateFrom.value = today;
  dateTo.value = today;
  timeFrom.value = "00:00";
  timeTo.value = "23:59";
  currentPage.value = 1;
};

// Enhanced stats
const stats = computed(() => {
  const all = props.valueBets;
  const filtered = filteredBets.value;
  const predictions = filtered.map(b => predictWinner(b));

  return {
    total: all.length,
    filtered: filtered.length,
    veryStrong: predictions.filter(p => p.strengthLevel === "very_strong").length,
    strong: predictions.filter(p => p.strengthLevel === "strong").length,
    moderate: predictions.filter(p => p.strengthLevel === "moderate").length,
    homeWins: predictions.filter(p => p.prediction_type === "home").length,
    awayWins: predictions.filter(p => p.prediction_type === "away").length,
    draws: predictions.filter(p => p.prediction_type === "draw").length,
    avgConfidence: predictions.length ? Math.round(predictions.reduce((sum, p) => sum + p.confidence, 0) / predictions.length) : 0
  };
});
</script>

<template>
  <Head title="Value Bets" />
  <AppLayout :breadcrumbs="breadcrumbs">
    <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-gray-950 dark:via-gray-900 dark:to-slate-900">
      <div class="flex flex-col gap-8 p-4 md:p-6 lg:p-8">

        <!-- MODERN HEADER STATS -->
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
          <div class="bg-white/70 dark:bg-gray-800/70 backdrop-blur-xl rounded-2xl p-4 border border-white/40 shadow-lg hover:shadow-xl transition-all duration-300">
            <div class="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">{{ stats.total }}</div>
            <div class="text-xs text-gray-600 dark:text-gray-400 font-medium">Total Matches</div>
          </div>

          <div class="bg-white/70 dark:bg-gray-800/70 backdrop-blur-xl rounded-2xl p-4 border border-white/40 shadow-lg hover:shadow-xl transition-all duration-300">
            <div class="text-2xl font-bold bg-gradient-to-r from-emerald-600 to-green-600 bg-clip-text text-transparent">{{ stats.filtered }}</div>
            <div class="text-xs text-gray-600 dark:text-gray-400 font-medium">Filtered</div>
          </div>

          <div class="bg-white/70 dark:bg-gray-800/70 backdrop-blur-xl rounded-2xl p-4 border border-white/40 shadow-lg hover:shadow-xl transition-all duration-300">
            <div class="text-2xl font-bold bg-gradient-to-r from-red-500 to-orange-500 bg-clip-text text-transparent">{{ stats.veryStrong }}</div>
            <div class="text-xs text-gray-600 dark:text-gray-400 font-medium">Very Strong</div>
          </div>

          <div class="bg-white/70 dark:bg-gray-800/70 backdrop-blur-xl rounded-2xl p-4 border border-white/40 shadow-lg hover:shadow-xl transition-all duration-300">
            <div class="text-2xl font-bold bg-gradient-to-r from-orange-500 to-yellow-500 bg-clip-text text-transparent">{{ stats.strong }}</div>
            <div class="text-xs text-gray-600 dark:text-gray-400 font-medium">Strong</div>
          </div>

          <div class="bg-white/70 dark:bg-gray-800/70 backdrop-blur-xl rounded-2xl p-4 border border-white/40 shadow-lg hover:shadow-xl transition-all duration-300">
            <div class="text-2xl font-bold bg-gradient-to-r from-blue-500 to-cyan-500 bg-clip-text text-transparent">{{ stats.homeWins }}</div>
            <div class="text-xs text-gray-600 dark:text-gray-400 font-medium">Home Wins</div>
          </div>

          <div class="bg-white/70 dark:bg-gray-800/70 backdrop-blur-xl rounded-2xl p-4 border border-white/40 shadow-lg hover:shadow-xl transition-all duration-300">
            <div class="text-2xl font-bold bg-gradient-to-r from-rose-500 to-pink-500 bg-clip-text text-transparent">{{ stats.awayWins }}</div>
            <div class="text-xs text-gray-600 dark:text-gray-400 font-medium">Away Wins</div>
          </div>

          <div class="bg-white/70 dark:bg-gray-800/70 backdrop-blur-xl rounded-2xl p-4 border border-white/40 shadow-lg hover:shadow-xl transition-all duration-300">
            <div class="text-2xl font-bold bg-gradient-to-r from-gray-500 to-slate-500 bg-clip-text text-transparent">{{ stats.draws }}</div>
            <div class="text-xs text-gray-600 dark:text-gray-400 font-medium">Draws</div>
          </div>

          <div class="bg-white/70 dark:bg-gray-800/70 backdrop-blur-xl rounded-2xl p-4 border border-white/40 shadow-lg hover:shadow-xl transition-all duration-300">
            <div class="text-2xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">{{ stats.avgConfidence }}%</div>
            <div class="text-xs text-gray-600 dark:text-gray-400 font-medium">Avg Confidence</div>
          </div>
        </div>

        <!-- ULTRA-MODERN FILTER PANEL -->
        <div class="bg-white/50 dark:bg-gray-800/50 backdrop-blur-2xl rounded-3xl border border-white/40 shadow-2xl p-6">
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">

            <!-- Date & Time Range -->
            <div class="space-y-3 col-span-full md:col-span-2">
              <label class="text-sm font-bold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <span class="text-blue-500">📅</span> Date & Time Range
              </label>
              <div class="grid grid-cols-2 gap-3">
                <div class="space-y-2">
                  <input type="date" v-model="dateFrom"
                    class="w-full rounded-xl border-0 bg-white/80 dark:bg-gray-700/80 px-3 py-2.5 text-sm shadow-lg ring-1 ring-gray-300/50 dark:ring-gray-600/50 focus:ring-2 focus:ring-indigo-500 backdrop-blur-sm transition-all duration-200">
                  <input type="time" v-model="timeFrom"
                    class="w-full rounded-xl border-0 bg-white/80 dark:bg-gray-700/80 px-3 py-2.5 text-sm shadow-lg ring-1 ring-gray-300/50 dark:ring-gray-600/50 focus:ring-2 focus:ring-indigo-500 backdrop-blur-sm transition-all duration-200">
                </div>
                <div class="space-y-2">
                  <input type="date" v-model="dateTo"
                    class="w-full rounded-xl border-0 bg-white/80 dark:bg-gray-700/80 px-3 py-2.5 text-sm shadow-lg ring-1 ring-gray-300/50 dark:ring-gray-600/50 focus:ring-2 focus:ring-indigo-500 backdrop-blur-sm transition-all duration-200">
                  <input type="time" v-model="timeTo"
                    class="w-full rounded-xl border-0 bg-white/80 dark:bg-gray-700/80 px-3 py-2.5 text-sm shadow-lg ring-1 ring-gray-300/50 dark:ring-gray-600/50 focus:ring-2 focus:ring-indigo-500 backdrop-blur-sm transition-all duration-200">
                </div>
              </div>
            </div>

            <!-- Search -->
            <div class="space-y-3">
              <label class="text-sm font-bold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <span class="text-green-500">🔍</span> Search Teams
              </label>
              <input type="text" placeholder="Team name..." v-model="searchTeam"
                class="w-full rounded-xl border-0 bg-white/80 dark:bg-gray-700/80 px-4 py-2.5 text-sm shadow-lg ring-1 ring-gray-300/50 dark:ring-gray-600/50 focus:ring-2 focus:ring-indigo-500 backdrop-blur-sm transition-all duration-200">
            </div>

            <!-- Strength Filter -->
            <div class="space-y-3">
              <label class="text-sm font-bold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <span class="text-orange-500">⚡</span> Strength Level
              </label>
              <select v-model="strengthFilter"
                class="w-full rounded-xl border-0 bg-white/80 dark:bg-gray-700/80 px-3 py-2.5 text-sm shadow-lg ring-1 ring-gray-300/50 dark:ring-gray-600/50 focus:ring-2 focus:ring-indigo-500 backdrop-blur-sm transition-all duration-200">
                <option value="all">All Strengths</option>
                <option value="very_strong">🔥 Very Strong (80%+)</option>
                <option value="strong">💪 Strong (70-79%)</option>
                <option value="moderate">⚖️ Moderate (60-69%)</option>
                <option value="weak">📉 Weak (&lt;60%)</option>
              </select>
            </div>

            <!-- Prediction Type -->
            <div class="space-y-3">
              <label class="text-sm font-bold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <span class="text-purple-500">🔮</span> Prediction
              </label>
              <select v-model="predictionFilter"
                class="w-full rounded-xl border-0 bg-white/80 dark:bg-gray-700/80 px-3 py-2.5 text-sm shadow-lg ring-1 ring-gray-300/50 dark:ring-gray-600/50 focus:ring-2 focus:ring-indigo-500 backdrop-blur-sm transition-all duration-200">
                <option value="all">All Predictions</option>
                <option value="home">🏠 Home Win</option>
                <option value="away">🛫 Away Win</option>
                <option value="draw">⚖️ Draw</option>
              </select>
            </div>

            <!-- Additional Filters Row -->
            <div class="space-y-3">
              <label class="text-sm font-bold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <span class="text-rose-500">📊</span> Min Matches
              </label>
              <input type="number" v-model.number="minMP" min="0" placeholder="0"
                class="w-full rounded-xl border-0 bg-white/80 dark:bg-gray-700/80 px-3 py-2.5 text-sm shadow-lg ring-1 ring-gray-300/50 dark:ring-gray-600/50 focus:ring-2 focus:ring-indigo-500 backdrop-blur-sm transition-all duration-200">
            </div>

            <div class="space-y-3">
              <label class="text-sm font-bold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <span class="text-yellow-500">🏆</span> Win Filter
              </label>
              <select v-model="winFilter"
                class="w-full rounded-xl border-0 bg-white/80 dark:bg-gray-700/80 px-3 py-2.5 text-sm shadow-lg ring-1 ring-gray-300/50 dark:ring-gray-600/50 focus:ring-2 focus:ring-indigo-500 backdrop-blur-sm transition-all duration-200">
                <option value="all">All Win Rates</option>
                <option value="high_wins">High Winners (5+)</option>
                <option value="low_wins">Low Winners (&lt;5)</option>
              </select>
            </div>

            <div class="space-y-3">
              <label class="text-sm font-bold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <span class="text-indigo-500">🎯</span> Rank Filter
              </label>
              <select v-model="rankFilter"
                class="w-full rounded-xl border-0 bg-white/80 dark:bg-gray-700/80 px-3 py-2.5 text-sm shadow-lg ring-1 ring-gray-300/50 dark:ring-gray-600/50 focus:ring-2 focus:ring-indigo-500 backdrop-blur-sm transition-all duration-200">
                <option value="all">All Ranks</option>
                <option value="top_ranked">Top Teams (1-3)</option>
                <option value="mid_ranked">Mid Teams (4-8)</option>
                <option value="low_ranked">Lower Teams (9+)</option>
              </select>
            </div>

            <div class="space-y-3">
              <label class="text-sm font-bold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <span class="text-cyan-500">📈</span> H2H Data
              </label>
              <select v-model="h2hFilter"
                class="w-full rounded-xl border-0 bg-white/80 dark:bg-gray-700/80 px-3 py-2.5 text-sm shadow-lg ring-1 ring-gray-300/50 dark:ring-gray-600/50 focus:ring-2 focus:ring-indigo-500 backdrop-blur-sm transition-all duration-200">
                <option value="all">All H2H</option>
                <option value="many_h2h">Rich History (4+)</option>
                <option value="few_h2h">Limited History (&lt;4)</option>
              </select>
            </div>

            <!-- Toggle & Reset -->
            <div class="space-y-3">
              <label class="text-sm font-bold text-gray-700 dark:text-gray-300">Quick Options</label>
              <div class="flex flex-col gap-3">
                <label class="flex items-center gap-2 text-sm font-medium cursor-pointer">
                  <input type="checkbox" v-model="showOnlyStrong"
                    class="rounded border-gray-300 text-indigo-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 transition-all duration-200">
                  <span class="text-orange-500">🔥</span> Strong Only (70%+)
                </label>
                <button @click="resetFilters"
                  class="px-4 py-2.5 rounded-xl text-sm font-medium bg-gradient-to-r from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-600 hover:from-indigo-100 hover:to-purple-100 dark:hover:from-gray-600 dark:hover:to-gray-500 transition-all duration-300 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5">
                  <span class="text-indigo-500">♻️</span> Reset All Filters
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- ULTRA-MODERN VALUE BET CARDS -->
        <div v-if="paginatedBets.length" class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6">
          <div v-for="bet in paginatedBets" :key="bet.id"
            class="group relative bg-white/60 dark:bg-gray-800/60 backdrop-blur-2xl rounded-3xl border border-white/40 shadow-xl hover:shadow-2xl transition-all duration-500 hover:-translate-y-3 hover:scale-[1.03] p-6 overflow-hidden">

            <!-- Dynamic background gradient -->
            <div :class="[
              'absolute inset-0 rounded-3xl opacity-20 transition-all duration-500',
              predictWinner(bet).strengthLevel === 'very_strong' ? 'bg-gradient-to-br from-red-500/30 via-orange-500/20 to-yellow-500/30' :
              predictWinner(bet).strengthLevel === 'strong' ? 'bg-gradient-to-br from-orange-500/25 via-yellow-500/15 to-green-500/25' :
              predictWinner(bet).strengthLevel === 'moderate' ? 'bg-gradient-to-br from-blue-500/20 via-indigo-500/10 to-purple-500/20' :
              'bg-gradient-to-br from-gray-500/15 via-slate-500/10 to-gray-600/15'
            ]"></div>

            <!-- Content -->
            <div class="relative z-10 space-y-4">
              <!-- Enhanced Prediction Badge -->
              <div class="flex justify-between items-start">
                <div class="flex flex-col gap-2">
                  <div :class="[
                    'px-3 py-1.5 rounded-full text-xs font-bold shadow-lg backdrop-blur-sm border border-white/40 transition-all duration-300',
                    predictWinner(bet).strengthLevel === 'very_strong'
                      ? 'bg-gradient-to-r from-red-500/90 to-orange-500/90 text-white shadow-red-200 animate-pulse'
                      : predictWinner(bet).strengthLevel === 'strong'
                        ? 'bg-gradient-to-r from-orange-500/85 to-yellow-500/85 text-white shadow-orange-200'
                        : predictWinner(bet).strengthLevel === 'moderate'
                          ? 'bg-gradient-to-r from-blue-500/80 to-indigo-500/80 text-white shadow-blue-200'
                          : 'bg-gradient-to-r from-gray-500/75 to-slate-500/75 text-white shadow-gray-200'
                  ]">
                    🔮 {{ predictWinner(bet).winner === 'draw' ? 'Draw' : predictWinner(bet).winner }} ({{ predictWinner(bet).confidence }}%)
                  </div>
                  <div class="text-xs text-gray-500 dark:text-gray-400 font-medium">
                    {{ predictWinner(bet).strengthLevel.replace('_', ' ').toUpperCase() }}
                  </div>
                </div>

                <!-- H2H Count Badge -->
                <div class="bg-indigo-500/20 border border-indigo-300/40 rounded-lg px-2 py-1 backdrop-blur-sm">
                  <div class="text-xs font-bold text-indigo-700 dark:text-indigo-300">
                    H2H: {{ bet.h2h_history?.length || 0 }}
                  </div>
                </div>
              </div>

              <!-- Date & Teams -->
              <div class="space-y-3">
                <div class="text-xs text-gray-500 dark:text-gray-400 font-semibold text-center bg-gray-100/50 dark:bg-gray-700/50 rounded-lg py-1 backdrop-blur-sm">
                  {{ formatDate(bet.match_date, bet.match_time) }}
                </div>
                <div class="text-center space-y-2">
                  <div class="text-base font-bold text-gray-800 dark:text-white truncate">{{ bet.home_team }}</div>
                  <div class="text-xs text-gray-500 dark:text-gray-400 font-bold">VS</div>
                  <div class="text-base font-bold text-gray-800 dark:text-white truncate">{{ bet.away_team }}</div>
                </div>
              </div>

              <!-- Enhanced Odds Display -->
              <div class="grid grid-cols-2 gap-3">
                <div :class="[
                  'rounded-xl p-3 text-center backdrop-blur-sm transition-all duration-300 border',
                  predictWinner(bet).prediction_type === 'home'
                    ? 'bg-gradient-to-br from-emerald-400/30 to-green-400/30 border-emerald-400/50 shadow-emerald-200/60 shadow-lg transform scale-105'
                    : 'bg-gradient-to-br from-emerald-400/15 to-green-400/15 border-emerald-300/30'
                ]">
                  <div class="text-xs text-emerald-700 dark:text-emerald-400 font-bold mb-1">🏠 HOME</div>
                  <div class="text-lg font-bold text-emerald-800 dark:text-emerald-300">{{ bet.home_odds }}</div>
                  <div class="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
                    {{ predictWinner(bet).homeWinRate }}% wins
                  </div>
                </div>
                <div :class="[
                  'rounded-xl p-3 text-center backdrop-blur-sm transition-all duration-300 border',
                  predictWinner(bet).prediction_type === 'away'
                    ? 'bg-gradient-to-br from-rose-400/30 to-red-400/30 border-rose-400/50 shadow-rose-200/60 shadow-lg transform scale-105'
                    : 'bg-gradient-to-br from-rose-400/15 to-red-400/15 border-rose-300/30'
                ]">
                  <div class="text-xs text-rose-700 dark:text-rose-400 font-bold mb-1">🛫 AWAY</div>
                  <div class="text-lg font-bold text-rose-800 dark:text-rose-300">{{ bet.away_odds }}</div>
                  <div class="text-xs text-rose-600 dark:text-rose-400 mt-1">
                    {{ predictWinner(bet).awayWinRate }}% wins
                  </div>
                </div>
              </div>

              <!-- Enhanced Standings Comparison -->
              <div class="grid grid-cols-2 gap-3">
                <div :class="[
                  'rounded-xl p-3 border backdrop-blur-sm transition-all duration-300',
                  predictWinner(bet).prediction_type === 'home'
                    ? 'bg-gradient-to-br from-emerald-100/60 to-green-100/60 border-emerald-400/60 shadow-emerald-200/60 shadow-lg'
                    : 'bg-gradient-to-br from-gray-100/40 to-gray-200/40 border-gray-300/40 dark:from-gray-700/40 dark:to-gray-600/40 dark:border-gray-600/40'
                ]">
                  <div class="text-[10px] uppercase text-gray-500 dark:text-gray-400 font-bold mb-2 flex justify-between">
                    <span>HOME</span>
                    <span class="text-indigo-600 font-bold">#{{ bet.home_rank }}</span>
                  </div>
                  <div class="space-y-1.5 text-xs">
                    <div class="grid grid-cols-3 gap-1 text-center">
                      <div class="bg-green-100/60 dark:bg-green-900/40 rounded px-1 py-0.5">
                        <div class="text-[9px] text-green-700 dark:text-green-400">W</div>
                        <div class="font-bold text-green-800 dark:text-green-300">{{ bet.home_wins ?? 0 }}</div>
                      </div>
                      <div class="bg-yellow-100/60 dark:bg-yellow-900/40 rounded px-1 py-0.5">
                        <div class="text-[9px] text-yellow-700 dark:text-yellow-400">D</div>
                        <div class="font-bold text-yellow-800 dark:text-yellow-300">{{ bet.home_draws ?? 0 }}</div>
                      </div>
                      <div class="bg-red-100/60 dark:bg-red-900/40 rounded px-1 py-0.5">
                        <div class="text-[9px] text-red-700 dark:text-red-400">L</div>
                        <div class="font-bold text-red-800 dark:text-red-300">{{ bet.home_losses ?? 0 }}</div>
                      </div>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-gray-600 dark:text-gray-400">Pts:</span>
                      <span class="font-bold text-indigo-600 dark:text-indigo-400">{{ bet.home_pts ?? 0 }}</span>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-gray-600 dark:text-gray-400">PPG:</span>
                      <span class="font-bold text-purple-600 dark:text-purple-400">{{ predictWinner(bet).homePPG }}</span>
                    </div>
                  </div>
                </div>

                <div :class="[
                  'rounded-xl p-3 border backdrop-blur-sm transition-all duration-300',
                  predictWinner(bet).prediction_type === 'away'
                    ? 'bg-gradient-to-br from-emerald-100/60 to-green-100/60 border-emerald-400/60 shadow-emerald-200/60 shadow-lg'
                    : 'bg-gradient-to-br from-gray-100/40 to-gray-200/40 border-gray-300/40 dark:from-gray-700/40 dark:to-gray-600/40 dark:border-gray-600/40'
                ]">
                  <div class="text-[10px] uppercase text-gray-500 dark:text-gray-400 font-bold mb-2 flex justify-between">
                    <span>AWAY</span>
                    <span class="text-indigo-600 font-bold">#{{ bet.away_rank }}</span>
                  </div>
                  <div class="space-y-1.5 text-xs">
                    <div class="grid grid-cols-3 gap-1 text-center">
                      <div class="bg-green-100/60 dark:bg-green-900/40 rounded px-1 py-0.5">
                        <div class="text-[9px] text-green-700 dark:text-green-400">W</div>
                        <div class="font-bold text-green-800 dark:text-green-300">{{ bet.away_wins ?? 0 }}</div>
                      </div>
                      <div class="bg-yellow-100/60 dark:bg-yellow-900/40 rounded px-1 py-0.5">
                        <div class="text-[9px] text-yellow-700 dark:text-yellow-400">D</div>
                        <div class="font-bold text-yellow-800 dark:text-yellow-300">{{ bet.away_draws ?? 0 }}</div>
                      </div>
                      <div class="bg-red-100/60 dark:bg-red-900/40 rounded px-1 py-0.5">
                        <div class="text-[9px] text-red-700 dark:text-red-400">L</div>
                        <div class="font-bold text-red-800 dark:text-red-300">{{ bet.away_losses ?? 0 }}</div>
                      </div>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-gray-600 dark:text-gray-400">Pts:</span>
                      <span class="font-bold text-indigo-600 dark:text-indigo-400">{{ bet.away_pts ?? 0 }}</span>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-gray-600 dark:text-gray-400">PPG:</span>
                      <span class="font-bold text-purple-600 dark:text-purple-400">{{ predictWinner(bet).awayPPG }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Always Open H2H History -->
              <div class="bg-white/30 dark:bg-gray-800/30 backdrop-blur-sm rounded-xl p-3 border border-white/40">
                <div class="text-xs font-bold text-gray-700 dark:text-gray-300 mb-2 flex items-center justify-between">
                  <span class="flex items-center gap-1">
                    📊 Head-to-Head History
                  </span>
                  <span class="text-indigo-600 dark:text-indigo-400">({{ bet.h2h_history?.length || 0 }})</span>
                </div>

                <div class="space-y-2 max-h-32 overflow-y-auto custom-scrollbar">
                  <div v-if="!bet.h2h_history?.length" class="text-xs text-gray-500 dark:text-gray-400 text-center py-2 italic">
                    No historical data available
                  </div>
                  <div v-else v-for="h in bet.h2h_history" :key="h.date"
                    class="bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm rounded-lg p-2 border border-white/30 hover:bg-white/70 dark:hover:bg-gray-800/70 transition-all duration-200">
                    <div class="flex justify-between items-center text-xs">
                      <div class="flex-1">
                        <div class="font-semibold text-gray-800 dark:text-gray-200">{{ h.date }}</div>
                        <div class="text-gray-500 dark:text-gray-400 text-[10px] mt-0.5 truncate">
                          {{ h.home_team }} vs {{ h.away_team }}
                        </div>
                      </div>
                      <div class="text-center ml-2">
                        <div class="font-bold text-sm bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                          {{ h.score }}
                        </div>
                        <div class="flex gap-1 text-[9px] mt-1" v-if="h.home_odds || h.away_odds">
                          <span class="text-emerald-600 font-medium" v-if="h.home_odds">{{ h.home_odds }}</span>
                          <span class="text-gray-400" v-if="h.draw_odds">{{ h.draw_odds }}</span>
                          <span class="text-rose-600 font-medium" v-if="h.away_odds">{{ h.away_odds }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- H2H Summary -->
                <div v-if="bet.h2h_history?.length" class="mt-2 pt-2 border-t border-white/30">
                  <div class="flex justify-between text-xs">
                    <span class="font-medium text-emerald-600 dark:text-emerald-400">
                      Home: {{ bet.home_wins_vs_away || 0 }} wins ({{ calcH2hPct(bet.home_wins_vs_away, bet.away_wins_vs_home).pHome }}%)
                    </span>
                    <span class="font-medium text-rose-600 dark:text-rose-400">
                      Away: {{ bet.away_wins_vs_home || 0 }} wins ({{ calcH2hPct(bet.home_wins_vs_away, bet.away_wins_vs_home).pAway }}%)
                    </span>
                  </div>
                </div>
              </div>

              <!-- Enhanced Footer -->
              <div class="flex justify-between items-center text-xs pt-2 border-t border-gray-200/50 dark:border-gray-700/50">
                <div class="flex items-center gap-2">
                  <a v-if="bet.match_url" :href="bet.match_url" target="_blank"
                    class="text-indigo-500 hover:text-indigo-600 dark:text-indigo-400 dark:hover:text-indigo-300 hover:underline transition-all duration-200 flex items-center gap-1 font-medium">
                    🔗 View Match
                  </a>
                  <span v-else class="text-gray-400">No link available</span>
                </div>
                <span class="text-gray-400 font-mono text-[10px] bg-gray-100/50 dark:bg-gray-700/50 px-2 py-1 rounded">
                  #{{ bet.id }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- No Results State -->
        <div v-else class="text-center py-16">
          <div class="text-8xl mb-6 animate-bounce">🔍</div>
          <div class="text-2xl font-bold text-gray-600 dark:text-gray-400 mb-3">No matches found</div>
          <div class="text-sm text-gray-500 dark:text-gray-500 mb-6 max-w-md mx-auto">
            Try adjusting your filters or search criteria to discover more betting opportunities
          </div>
          <button @click="resetFilters"
            class="px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl font-medium hover:from-indigo-600 hover:to-purple-700 transition-all duration-300 shadow-lg hover:shadow-xl transform hover:-translate-y-1">
            Reset All Filters
          </button>
        </div>

        <!-- Ultra-Modern Pagination -->
        <div class="flex flex-col sm:flex-row justify-between items-center gap-4" v-if="totalPages > 1">
          <!-- Page Info -->
          <div class="text-sm text-gray-600 dark:text-gray-400 font-medium">
            Showing {{ ((currentPage - 1) * perPage) + 1 }} to {{ Math.min(currentPage * perPage, totalBets) }} of {{ totalBets }} matches
          </div>

          <!-- Pagination Controls -->
          <div class="flex items-center gap-2">
            <button :disabled="currentPage === 1" @click="goToPage(1)"
              class="px-3 py-2 rounded-xl text-sm font-medium bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-white/30 hover:bg-white/80 dark:hover:bg-gray-800/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg">
              ⏮️
            </button>

            <button :disabled="currentPage === 1" @click="goToPage(currentPage - 1)"
              class="px-4 py-2 rounded-xl text-sm font-medium bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-white/30 hover:bg-white/80 dark:hover:bg-gray-800/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg">
              ← Previous
            </button>

            <div class="flex gap-1">
              <span v-if="visiblePages[0] > 1" class="px-3 py-2 text-sm text-gray-500">...</span>
              <button v-for="page in visiblePages" :key="page"
                @click="goToPage(page)"
                :class="[
                  'px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 shadow-lg backdrop-blur-sm border',
                  page === currentPage
                    ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white border-indigo-500 shadow-indigo-200 transform scale-110'
                    : 'bg-white/60 dark:bg-gray-800/60 border-white/30 hover:bg-white/80 dark:hover:bg-gray-800/80 hover:scale-105'
                ]">
                {{ page }}
              </button>
              <span v-if="visiblePages[visiblePages.length - 1] < totalPages" class="px-3 py-2 text-sm text-gray-500">...</span>
            </div>

            <button :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)"
              class="px-4 py-2 rounded-xl text-sm font-medium bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-white/30 hover:bg-white/80 dark:hover:bg-gray-800/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg">
              Next →
            </button>

            <button :disabled="currentPage === totalPages" @click="goToPage(totalPages)"
              class="px-3 py-2 rounded-xl text-sm font-medium bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-white/30 hover:bg-white/80 dark:hover:bg-gray-800/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg">
              ⏭️
            </button>
          </div>

          <!-- Per Page Selector -->
          <div class="flex items-center gap-2 text-sm">
            <label class="text-gray-600 dark:text-gray-400 font-medium">Show:</label>
            <select v-model="perPage" @change="currentPage = 1"
              class="rounded-lg border-0 bg-white/80 dark:bg-gray-700/80 px-3 py-1.5 text-sm shadow-md ring-1 ring-gray-300/50 dark:ring-gray-600/50 focus:ring-2 focus:ring-indigo-500 backdrop-blur-sm transition-all duration-200">
              <option value="12">12</option>
              <option value="24">24</option>
              <option value="48">48</option>
              <option value="96">96</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 2px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(99, 102, 241, 0.5);
  border-radius: 2px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(99, 102, 241, 0.7);
}
</style>
