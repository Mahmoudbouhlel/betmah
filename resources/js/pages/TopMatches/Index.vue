<script setup lang="ts">
import AppLayout from '@/layouts/AppLayout.vue'
import { Head, router } from '@inertiajs/vue3'
import { ref } from 'vue'

const props = defineProps<{
  topMatches: Array<any>;
  date: string;
  totalMatches: number;
}>()

// state pour le filtre date
const selectedDate = ref(props.date)

// quand l’utilisateur change la date
const applyDateFilter = () => {
  router.get(
    '/top-matches',   // URL directe
    { date: selectedDate.value },
    { preserveScroll: true, preserveState: true }
  )
}


// couleurs du score
const getConfidenceColor = (score: number) => {
  if (score >= 80) return 'bg-green-500'
  if (score >= 65) return 'bg-blue-500'
  if (score >= 50) return 'bg-yellow-500'
  return 'bg-gray-400'
}

// badge
const getConfidenceBadge = (score: number) => {
  if (score >= 80) return { text: 'Very High', icon: '🔥' }
  if (score >= 65) return { text: 'High', icon: '⚡' }
  if (score >= 50) return { text: 'Medium', icon: '💫' }
  return { text: 'Low', icon: '⭐' }
}

// emoji gagnant
const getPredictionEmoji = (winner: string) => {
  if (winner === 'home') return '🏠'
  if (winner === 'away') return '✈️'
  return '🤝'
}
</script>

<template>
  <Head title="AI Match Predictions" />
  <AppLayout>
    <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div class="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">

        <!-- Header -->
        <div class="text-center mb-8">
          <h1 class="text-4xl font-extrabold text-indigo-600 dark:text-indigo-400">
            AI Match Predictions
          </h1>
          <p class="text-lg text-gray-600 dark:text-gray-300 mt-2">
            {{ totalMatches }} matches pour la date : {{ date }}
          </p>
        </div>

        <!-- Date Filter -->
        <div class="flex justify-center mb-10">
          <div class="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-md flex items-center space-x-3">
            <input
              type="date"
              v-model="selectedDate"
              class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-indigo-500"
            />
            <button
              @click="applyDateFilter"
              class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg shadow transition"
            >
              Filter
            </button>
          </div>
        </div>

        <!-- Matches Grid -->
        <div class="grid gap-6 lg:grid-cols-2">
          <div v-for="m in topMatches" :key="m.id"
               class="group bg-white dark:bg-gray-800 rounded-3xl shadow-xl hover:shadow-2xl transition-all duration-300 overflow-hidden border border-gray-100 dark:border-gray-700">

            <!-- Card Header -->
            <div class="bg-gradient-to-r from-blue-500 to-indigo-600 px-6 py-4 flex justify-between items-center">
              <div class="flex items-center space-x-2 text-white/80 text-sm">
                <span>{{ m.match_date }}</span>
                <span>•</span>
                <span>{{ m.match_time }}</span>
              </div>
              <a :href="m.match_url" target="_blank"
                 class="px-3 py-1 bg-white/20 hover:bg-white/30 rounded-lg text-white text-sm font-medium transition-colors">
                View ↗
              </a>
            </div>

            <!-- Card Body -->
            <div class="p-6">
              <!-- Confidence -->
              <div class="mb-6">
                <div class="inline-flex items-center space-x-2 px-4 py-2 rounded-full font-semibold bg-gray-100 dark:bg-gray-700">
                  <span>{{ getConfidenceBadge(m.win_probability).icon }}</span>
                  <span class="text-sm">{{ m.win_probability }}% Confidence</span>
                  <span class="text-xs opacity-75">({{ getConfidenceBadge(m.win_probability).text }})</span>
                </div>
                <div class="w-full mt-2 bg-gray-200 rounded-full h-2 dark:bg-gray-700">
                  <div class="h-2 rounded-full"
                       :class="getConfidenceColor(m.win_probability)"
                       :style="{ width: m.win_probability + '%' }">
                  </div>
                </div>
              </div>

              <!-- Teams -->
              <div class="mb-6">
                <!-- Home -->
                <div class="flex items-center justify-between mb-4 p-4 rounded-2xl"
                     :class="m.predicted_winner === 'home' ? 'bg-green-50 dark:bg-green-900/20 ring-2 ring-green-500' : 'bg-gray-50 dark:bg-gray-700/50'">
                  <div class="flex items-center space-x-3">
                    <span v-if="m.predicted_winner === 'home'" class="text-2xl">{{ getPredictionEmoji('home') }}</span>
                    <div>
                      <h3 class="font-bold text-lg">{{ m.home_team }}</h3>
                      <p class="text-xs text-gray-500">Rank #{{ m.home_rank }}</p>
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-2xl font-bold">{{ m.home_odds }}</div>
                    <div class="text-xs text-gray-500">Odds</div>
                  </div>
                </div>

                <!-- VS -->
                <div class="text-center py-2">
                  <span class="text-2xl font-bold text-gray-400">VS</span>
                </div>

                <!-- Away -->
                <div class="flex items-center justify-between p-4 rounded-2xl"
                     :class="m.predicted_winner === 'away' ? 'bg-green-50 dark:bg-green-900/20 ring-2 ring-green-500' : 'bg-gray-50 dark:bg-gray-700/50'">
                  <div class="flex items-center space-x-3">
                    <span v-if="m.predicted_winner === 'away'" class="text-2xl">{{ getPredictionEmoji('away') }}</span>
                    <div>
                      <h3 class="font-bold text-lg">{{ m.away_team }}</h3>
                      <p class="text-xs text-gray-500">Rank #{{ m.away_rank }}</p>
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-2xl font-bold">{{ m.away_odds }}</div>
                    <div class="text-xs text-gray-500">Odds</div>
                  </div>
                </div>
              </div>

              <!-- Analysis -->
              <div class="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-gray-900/40 dark:to-indigo-900/20 rounded-xl border border-blue-200 dark:border-blue-700">
                <p class="text-sm text-gray-800 dark:text-gray-200 text-center">
                  {{ m.analysis }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="mt-12 text-center">
          <div class="inline-flex items-center space-x-2 px-6 py-3 bg-white dark:bg-gray-800 rounded-full shadow-lg">
            <span class="text-sm text-gray-600 dark:text-gray-300">
              ⚠️ Predictions are based on statistics. Bet responsibly.
            </span>
          </div>
        </div>

      </div>
    </div>
  </AppLayout>
</template>
