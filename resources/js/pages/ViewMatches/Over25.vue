<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  matches: {
    type: Array,
    default: () => []
  }
});

/* ---------- Helpers ---------- */

// convert to array (protect against Inertia object behavior)
function toArray(val) {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  return Object.values(val);
}

// safe rank parsing (e.g. "6.")
function parseRank(val) {
  if (!val) return 999;
  const n = parseInt(String(val).replace(/\D/g, ''));
  return isNaN(n) ? 999 : n;
}

// Implied probability from odds
function probFromOdds(odds) {
  const n = Number(String(odds).replace(',', '.'));
  if (!isFinite(n) || n <= 0) return 0;
  return +(100 / n).toFixed(1);
}

// Strong home detection
function isStrongHome(m) {
  return (
    parseRank(m.home_rank) < parseRank(m.away_rank) &&
    Number(m.home_pts || 0) > Number(m.away_pts || 0) &&
    Number(String(m.home_odds).replace(',', '.')) > 1.5
  );
}

/* ---------- Sparkline ---------- */
function buildSparklinePath(values = [], width = 80, height = 24) {
  if (!values.length) return '';
  const nums = values.map(v => Number(String(v).replace(',', '.'))).filter(isFinite);
  if (!nums.length) return '';

  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const range = max - min || 1;
  const step = width / (nums.length - 1);

  return 'M' + nums
    .map((v, i) => {
      const x = i * step;
      const y = height - ((v - min) / range) * height;
      return `${x},${y}`;
    })
    .join(' L ');
}

/* ---------- Filters & Sorting ---------- */

const filters = ref({
  strongHome: false,
  valueBet: false
});

const sortBy = ref('match_date'); // match_date | home_odds | home_rank | probability
const sortDir = ref('asc');

function isValueBet(m) {
  const o = Number(String(m.home_odds).replace(',', '.'));
  const p = probFromOdds(o);
  return o >= 1.5 && o <= 2.3 && p >= 40;
}

/* ---------- Filtering ---------- */

const filtered = computed(() => {
  return toArray(props.matches).filter(m => {
    if (filters.value.strongHome && !isStrongHome(m)) return false;
    if (filters.value.valueBet && !isValueBet(m)) return false;
    return true;
  });
});

/* ---------- Sorting ---------- */

const sorted = computed(() => {
  const arr = filtered.value.slice();

  arr.forEach(m => {
    m._prob = probFromOdds(m.home_odds);
    m._home_rank_num = parseRank(m.home_rank);
  });

  const key = sortBy.value;
  const dir = sortDir.value === 'asc' ? 1 : -1;

  arr.sort((a, b) => {
    let va, vb;
    if (key === 'home_odds') {
      va = Number(a.home_odds);
      vb = Number(b.home_odds);
    } else if (key === 'home_rank') {
      va = a._home_rank_num;
      vb = b._home_rank_num;
    } else if (key === 'probability') {
      va = a._prob;
      vb = b._prob;
    } else {
      va = a.match_date + ' ' + a.match_time;
      vb = b.match_date + ' ' + b.match_time;
    }

    return (va < vb ? -1 : va > vb ? 1 : 0) * dir;
  });

  return arr;
});

/* ---------- Pagination ---------- */

const page = ref(1);
const perPage = ref(12);

const totalPages = computed(() =>
  Math.max(1, Math.ceil(sorted.value.length / perPage.value))
);

const paginated = computed(() => {
  const start = (page.value - 1) * perPage.value;
  return sorted.value.slice(start, start + perPage.value);
});

function gotoPage(p) {
  page.value = Math.max(1, Math.min(totalPages.value, p));
}
</script>

<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold">Match Details</h1>

      <div class="flex items-center gap-3">
        <label class="text-sm text-gray-600">Per page</label>
        <select v-model.number="perPage" class="border rounded px-2 py-1 text-sm">
          <option :value="6">6</option>
          <option :value="12">12</option>
          <option :value="24">24</option>
        </select>
      </div>
    </div>

    <!-- FILTERS -->
    <div class="flex gap-4">
      <label class="flex items-center gap-2 text-sm">
        <input type="checkbox" v-model="filters.strongHome" />
        Strong Home
      </label>

      <label class="flex items-center gap-2 text-sm">
        <input type="checkbox" v-model="filters.valueBet" />
        Value Bets
      </label>
    </div>

    <!-- SORT -->
    <div class="flex gap-3">
      <button @click="sortBy = 'match_date'; sortDir = sortDir==='asc'?'desc':'asc'"
        class="px-3 py-1 border rounded text-sm">
        Sort Date
      </button>

      <button @click="sortBy = 'home_odds'; sortDir = sortDir==='asc'?'desc':'asc'"
        class="px-3 py-1 border rounded text-sm">
        Sort Odds
      </button>

      <button @click="sortBy = 'home_rank'; sortDir = sortDir==='asc'?'desc':'asc'"
        class="px-3 py-1 border rounded text-sm">
        Sort Rank
      </button>

      <button @click="sortBy = 'probability'; sortDir = sortDir==='asc'?'desc':'asc'"
        class="px-3 py-1 border rounded text-sm">
        Sort Probability
      </button>
    </div>

    <!-- GRID -->
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      <div
        v-for="m in paginated"
        :key="m.match_id"
        class="bg-white shadow rounded-2xl p-4 border border-gray-100 hover:shadow-lg transition"
      >
        <!-- Header -->
        <div class="flex justify-between">
          <div>
            <div class="text-lg font-semibold">
              {{ m.home_team }}
              <span class="text-gray-400 mx-2">vs</span>
              {{ m.away_team }}
            </div>
            <div class="text-xs text-gray-500 mt-1">
              {{ m.match_date }} • {{ m.match_time }}
            </div>
          </div>

          <div class="text-xs text-gray-500">ID {{ m.match_id }}</div>
        </div>

        <!-- Odds + Probability -->
        <div class="mt-3 flex justify-between gap-4">
          <div class="text-center">
            <div class="text-xs text-gray-500">Home</div>
            <div class="text-xl font-bold text-green-600">{{ m.home_odds }}</div>
          </div>

          <div class="w-32">
            <div class="text-xs text-gray-500">Implied Prob</div>
            <div class="bg-gray-200 h-2 rounded mt-1">
              <div
                class="h-2 rounded bg-blue-500"
                :style="{ width: probFromOdds(m.home_odds) + '%' }"
              ></div>
            </div>
            <div class="text-xs text-right mt-1 text-gray-600">
              {{ probFromOdds(m.home_odds) }}%
            </div>
          </div>
        </div>

        <!-- Rank Chips -->
        <div class="mt-4 flex gap-4">
          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-500">Home Rank</span>
            <span
              class="px-2 py-1 rounded text-sm font-semibold"
              :class="parseRank(m.home_rank) <= 5
                ? 'bg-green-100 text-green-700'
                : parseRank(m.home_rank) <= 10
                  ? 'bg-yellow-100 text-yellow-700'
                  : 'bg-red-100 text-red-700'"
            >
              {{ m.home_rank }}
            </span>
          </div>

          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-500">Away Rank</span>
            <span
              class="px-2 py-1 rounded text-sm font-semibold"
              :class="parseRank(m.away_rank) <= 5
                ? 'bg-green-100 text-green-700'
                : parseRank(m.away_rank) <= 10
                  ? 'bg-yellow-100 text-yellow-700'
                  : 'bg-red-100 text-red-700'"
            >
              {{ m.away_rank }}
            </span>
          </div>
        </div>

        <!-- Sparkline -->
        <div class="mt-4">
          <div v-if="m.odds_trend && m.odds_trend.length">
            <svg viewBox="0 0 80 24" class="w-20 h-6 text-gray-500">
              <path
                :d="buildSparklinePath(m.odds_trend)"
                stroke="currentColor"
                stroke-width="1.5"
                fill="none"
              />
            </svg>
          </div>
        </div>

        <!-- CTA -->
        <div class="mt-4 flex justify-between items-center">
          <div class="text-xs text-gray-600">
            Prediction:
            <span class="font-semibold">
              {{ isStrongHome(m) ? 'Home Favored' : 'Toss-up' }}
            </span>
          </div>

          <a
            :href="m.match_url || '#'"
            target="_blank"
            class="text-xs px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
          >
            View
          </a>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div class="flex items-center justify-between mt-8">
      <div class="text-sm text-gray-600">
        Showing {{ (page - 1) * perPage + 1 }} –
        {{ Math.min(page * perPage, sorted.length) }}
        of {{ sorted.length }}
      </div>

      <div class="flex gap-2">
        <button @click="gotoPage(1)" class="px-3 py-1 border rounded">First</button>
        <button @click="gotoPage(page - 1)" class="px-3 py-1 border rounded">Prev</button>

        <span class="px-3 py-1 border rounded bg-white text-sm">
          Page {{ page }} / {{ totalPages }}
        </span>

        <button @click="gotoPage(page + 1)" class="px-3 py-1 border rounded">Next</button>
        <button @click="gotoPage(totalPages)" class="px-3 py-1 border rounded">Last</button>
      </div>
    </div>
  </div>
</template>
