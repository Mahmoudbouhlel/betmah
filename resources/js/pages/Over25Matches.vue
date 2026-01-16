<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
    <!-- Upload Screen -->
    <div v-if="!data" class="min-h-screen flex items-center justify-center p-8">
      <div class="max-w-4xl w-full fade-in-up">
        <div class="text-center mb-12">
          <h1 class="text-6xl font-bold text-white mb-4 gradient-text pulse-animation">
            📊 Performance Dashboard
          </h1>
          <p class="text-purple-200 text-xl">Visualisez vos KPIs avec élégance</p>
        </div>

        <div class="glass-card rounded-3xl p-16 upload-zone" @dragover.prevent @drop.prevent="handleDrop">
          <label class="flex flex-col items-center justify-center cursor-pointer group">
            <div class="w-40 h-40 bg-purple-500/20 rounded-full flex items-center justify-center mb-8 group-hover:bg-purple-500/30 transition-all duration-300 shimmer">
              <svg class="w-20 h-20 text-purple-300 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
              </svg>
            </div>
            <span class="text-2xl text-white font-bold mb-3">Déposez votre fichier JSON</span>
            <span class="text-purple-300 text-lg">ou cliquez pour parcourir</span>
            <input type="file" accept=".json" @change="handleFileUpload" class="hidden">
          </label>
        </div>
      </div>
    </div>

    <!-- Dashboard -->
    <div v-else class="p-8">
      <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <div class="flex justify-between items-center mb-8 slide-in">
          <div>
            <h1 class="text-5xl font-bold text-white mb-2">{{ data.Dashboard }}</h1>
            <p class="text-purple-200 text-lg">🚀 Analytics en temps réel</p>
          </div>
          <div class="flex gap-4">
            <button @click="showKpiSelector = true" class="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white px-6 py-3 rounded-xl font-semibold shadow-lg hover:shadow-2xl transform hover:scale-105 transition-all duration-300 flex items-center gap-2">
              ⚙️ Configurer KPIs
            </button>
            <button @click="resetDashboard" class="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-6 py-3 rounded-xl font-semibold shadow-lg hover:shadow-2xl transform hover:scale-105 transition-all duration-300 flex items-center gap-2">
              🔄 Nouveau Fichier
            </button>
          </div>
        </div>

        <!-- KPI Selector Modal -->
        <div v-if="showKpiSelector" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" @click.self="showKpiSelector = false">
          <div class="glass-card rounded-3xl p-8 max-w-4xl w-full max-h-[80vh] overflow-y-auto">
            <div class="flex justify-between items-center mb-6">
              <h2 class="text-3xl font-bold text-white">🎯 Sélectionner les KPIs à afficher</h2>
              <button @click="showKpiSelector = false" class="text-white hover:text-purple-300 text-2xl">✕</button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div v-for="section in allSections" :key="section.name"
                   @click="toggleKpi(section.name)"
                   class="glass-card p-4 rounded-xl cursor-pointer transition-all duration-300 hover:scale-105"
                   :class="selectedKpis.includes(section.name) ? 'border-2 border-purple-500 bg-purple-500/20' : 'border border-white/20'">
                <div class="flex items-center gap-3">
                  <div class="text-3xl">{{ section.icon }}</div>
                  <div class="flex-1">
                    <h3 class="text-white font-semibold">{{ section.name }}</h3>
                    <p class="text-purple-200 text-sm">{{ section.unit }}</p>
                  </div>
                  <div class="text-2xl">
                    {{ selectedKpis.includes(section.name) ? '✅' : '⬜' }}
                  </div>
                </div>
              </div>
            </div>

            <div class="flex justify-end gap-4">
              <button @click="selectAllKpis" class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-semibold transition-all">
                Tout sélectionner
              </button>
              <button @click="showKpiSelector = false" class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-xl font-semibold transition-all">
                Appliquer
              </button>
            </div>
          </div>
        </div>

        <!-- KPI Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div v-for="(kpi, idx) in visibleKpiCards" :key="idx"
               class="glass-card rounded-2xl p-6 kpi-card fade-in-up"
               :style="{ animationDelay: idx * 0.05 + 's' }">
            <div class="flex items-start justify-between mb-4">
              <div class="text-4xl">{{ kpi.icon }}</div>
              <span :class="kpi.trend > 0 ? 'text-green-400' : 'text-red-400'" class="text-2xl font-bold">
                {{ kpi.trend > 0 ? '↗' : '↘' }}
              </span>
            </div>
            <h3 class="text-purple-200 text-sm mb-2 font-medium">{{ kpi.title }}</h3>
            <div class="flex items-baseline gap-2">
              <span class="text-4xl font-bold text-white">{{ kpi.value }}</span>
              <span class="text-purple-300 text-sm">{{ kpi.unit }}</span>
            </div>
            <div class="mt-3 flex items-center gap-2">
              <span :class="kpi.trend > 0 ? 'text-green-400' : 'text-red-400'" class="text-sm font-semibold">
                {{ Math.abs(kpi.trend) }}%
              </span>
              <span class="text-purple-300 text-xs">vs budget</span>
            </div>
          </div>
        </div>

        <!-- Filters -->
        <div class="glass-card rounded-2xl p-6 mb-8 fade-in-up">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-purple-200 text-sm font-medium mb-2">📊 Section</label>
              <select v-model="selectedSection" @change="updateCharts"
                      class="w-full bg-slate-800/50 text-white border border-purple-400/30 rounded-xl px-4 py-3 focus:outline-none focus:border-purple-400 transition-all">
                <option v-for="section in sections" :key="section" :value="section">{{ section }}</option>
              </select>
            </div>
            <div>
              <label class="block text-purple-200 text-sm font-medium mb-2">🏭 Site</label>
              <select v-model="selectedSite" @change="updateCharts"
                      class="w-full bg-slate-800/50 text-white border border-purple-400/30 rounded-xl px-4 py-3 focus:outline-none focus:border-purple-400 transition-all">
                <option v-for="site in sites" :key="site" :value="site">{{ site }}</option>
              </select>
            </div>
            <div>
              <label class="block text-purple-200 text-sm font-medium mb-2">📈 Type de Chart</label>
              <select v-model="chartType" @change="updateCharts"
                      class="w-full bg-slate-800/50 text-white border border-purple-400/30 rounded-xl px-4 py-3 focus:outline-none focus:border-purple-400 transition-all">
                <option value="line">Line</option>
                <option value="bar">Bar</option>
                <option value="radar">Radar</option>
                <option value="polarArea">Polar Area</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Comparison Table -->
        <div class="glass-card rounded-2xl p-6 mb-8 fade-in-up">
          <h2 class="text-2xl font-bold text-white mb-6 flex items-center gap-2">
            <span class="text-3xl">📋</span> Tableau de Comparaison
          </h2>
          <div class="overflow-x-auto">
            <table class="w-full text-left">
              <thead>
                <tr class="border-b border-purple-400/30">
                  <th class="text-purple-200 font-semibold py-3 px-4">Mois</th>
                  <th class="text-purple-200 font-semibold py-3 px-4">Actual</th>
                  <th class="text-purple-200 font-semibold py-3 px-4">Budget</th>
                  <th class="text-purple-200 font-semibold py-3 px-4">Variance</th>
                  <th class="text-purple-200 font-semibold py-3 px-4">%</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in comparisonTableData" :key="idx"
                    class="border-b border-white/10 hover:bg-white/5 transition-colors">
                  <td class="text-white py-3 px-4 font-medium">{{ row.month }}</td>
                  <td class="text-white py-3 px-4">{{ row.actual }}</td>
                  <td class="text-white py-3 px-4">{{ row.budget }}</td>
                  <td :class="row.variance >= 0 ? 'text-green-400' : 'text-red-400'" class="py-3 px-4 font-semibold">
                    {{ row.variance >= 0 ? '+' : '' }}{{ row.variance }}
                  </td>
                  <td :class="row.percentage >= 0 ? 'text-green-400' : 'text-red-400'" class="py-3 px-4 font-semibold">
                    {{ row.percentage >= 0 ? '+' : '' }}{{ row.percentage }}%
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Fixed Charts Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <!-- Trend Chart -->
          <div class="glass-card rounded-2xl p-6 fade-in-up">
            <h2 class="text-2xl font-bold text-white mb-6 flex items-center gap-2">
              <span class="text-3xl">📈</span> Analyse des Tendances
            </h2>
            <div class="h-80">
              <canvas ref="trendChart"></canvas>
            </div>
          </div>

          <!-- Comparison Chart -->
          <div class="glass-card rounded-2xl p-6 fade-in-up">
            <h2 class="text-2xl font-bold text-white mb-6 flex items-center gap-2">
              <span class="text-3xl">📊</span> Comparaison Performance
            </h2>
            <div class="h-80">
              <canvas ref="comparisonChart"></canvas>
            </div>
          </div>

          <!-- Pie Chart -->
          <div class="glass-card rounded-2xl p-6 fade-in-up">
            <h2 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <span class="text-2xl">🎯</span> Répartition
            </h2>
            <div class="h-80">
              <canvas ref="pieChart"></canvas>
            </div>
          </div>

          <!-- Radar Chart -->
          <div class="glass-card rounded-2xl p-6 fade-in-up">
            <h2 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <span class="text-2xl">🌟</span> Performance Radar
            </h2>
            <div class="h-80">
              <canvas ref="radarChart"></canvas>
            </div>
          </div>

          <!-- Polar Chart -->
          <div class="glass-card rounded-2xl p-6 fade-in-up lg:col-span-2">
            <h2 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <span class="text-2xl">⚡</span> Polar View
            </h2>
            <div class="h-80">
              <canvas ref="polarChart"></canvas>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onBeforeUnmount, watch } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const data = ref(null)
const selectedSection = ref('OEE Net')
const selectedSite = ref('Sousse')
const chartType = ref('line')
const charts = ref({})
const allKpiCards = ref([])
const selectedKpis = ref([])
const showKpiSelector = ref(false)

const trendChart = ref(null)
const comparisonChart = ref(null)
const pieChart = ref(null)
const radarChart = ref(null)
const polarChart = ref(null)

const sections = computed(() => {
  return data.value ? data.value.sections.map(s => s.section) : []
})

const sites = computed(() => {
  if (!data.value || !data.value.sections[0]) return []
  return data.value.sections[0].rows.map(r => r.site).filter(s => s !== data.value.sections[0].section)
})

const allSections = computed(() => {
  if (!data.value) return []
  const icons = ['⚡', '💰', '📊', '🎯', '🔥', '💎', '🚀', '⭐', '🎨', '🌈', '🎪', '🎭']
  return data.value.sections.map((section, idx) => ({
    name: section.section,
    unit: section.rows[0]?.values?.Unnamed || '',
    icon: icons[idx % icons.length]
  }))
})

const visibleKpiCards = computed(() => {
  return allKpiCards.value.filter(kpi => selectedKpis.value.includes(kpi.title))
})

const comparisonTableData = computed(() => {
  const chartData = getChartData()
  return chartData.labels.map((month, idx) => {
    const actual = parseFloat(chartData.actual[idx])
    const budget = parseFloat(chartData.budget[idx])
    const variance = (actual - budget).toFixed(2)
    const percentage = budget !== 0 ? ((variance / budget) * 100).toFixed(2) : 0
    return {
      month,
      actual: actual.toFixed(2),
      budget: budget.toFixed(2),
      variance,
      percentage
    }
  })
})

const handleFileUpload = (e) => {
  const file = e.target.files[0]
  if (file) readFile(file)
}

const handleDrop = (e) => {
  const file = e.dataTransfer.files[0]
  if (file) readFile(file)
}

const readFile = (file) => {
  const reader = new FileReader()
  reader.onload = (event) => {
    try {
      data.value = JSON.parse(event.target.result)
      nextTick(() => {
        calculateKPIs()
        updateCharts()
      })
    } catch (error) {
      alert('Fichier JSON invalide')
    }
  }
  reader.readAsText(file)
}

const calculateKPIs = () => {
  const icons = ['⚡', '💰', '📊', '🎯', '🔥', '💎', '🚀', '⭐', '🎨', '🌈', '🎪', '🎭']
  allKpiCards.value = data.value.sections.map((section, idx) => {
    const total = section.rows.reduce((sum, row) => {
      const values = Object.values(row.values).filter(v => typeof v === 'number')
      return sum + values.reduce((a, b) => a + b, 0)
    }, 0)
    return {
      title: section.section,
      value: total.toFixed(2),
      unit: section.rows[0]?.values?.Unnamed || '',
      trend: Math.random() > 0.5 ? parseFloat((Math.random() * 20).toFixed(1)) : -parseFloat((Math.random() * 20).toFixed(1)),
      icon: icons[idx % icons.length]
    }
  })

  // Select first 8 by default
  selectedKpis.value = allKpiCards.value.slice(0, 8).map(kpi => kpi.title)
}

const toggleKpi = (kpiName) => {
  const index = selectedKpis.value.indexOf(kpiName)
  if (index > -1) {
    selectedKpis.value.splice(index, 1)
  } else {
    selectedKpis.value.push(kpiName)
  }
}

const selectAllKpis = () => {
  selectedKpis.value = allKpiCards.value.map(kpi => kpi.title)
}

const getChartData = () => {
  const section = data.value.sections.find(s => s.section === selectedSection.value)
  if (!section) return { labels: [], actual: [], budget: [] }

  const siteData = section.rows.find(r => r.site === selectedSite.value)
  if (!siteData) return { labels: [], actual: [], budget: [] }

  const months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
  const labels = []
  const actual = []
  const budget = []

  Object.keys(siteData.values).forEach(key => {
    if (key.includes('2024') && key.includes('-01 00:00:00')) {
      const match = key.match(/2024-(\d{2})-01/)
      if (match) {
        const monthIdx = parseInt(match[1]) - 1
        labels.push(months[monthIdx])
        actual.push((siteData.values[key] * 100).toFixed(2))
        const budgetKey = key.replace('Actual', 'Budget')
        budget.push(siteData.values[budgetKey] ? (siteData.values[budgetKey] * 100).toFixed(2) : 0)
      }
    }
  })

  return { labels, actual, budget }
}

const updateCharts = () => {
  const chartData = getChartData()

  // Destroy existing charts
  Object.values(charts.value).forEach(chart => chart?.destroy())
  charts.value = {}

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        labels: { color: '#a78bfa', font: { size: 12 } }
      }
    },
    scales: {
      y: {
        ticks: { color: '#a78bfa' },
        grid: { color: 'rgba(255,255,255,0.1)' }
      },
      x: {
        ticks: { color: '#a78bfa' },
        grid: { color: 'rgba(255,255,255,0.1)' }
      }
    }
  }

  // Trend Chart
  if (trendChart.value) {
    charts.value.trend = new Chart(trendChart.value, {
      type: chartType.value,
      data: {
        labels: chartData.labels,
        datasets: [{
          label: 'Actual',
          data: chartData.actual,
          borderColor: '#8b5cf6',
          backgroundColor: 'rgba(139, 92, 246, 0.2)',
          tension: 0.4,
          fill: true
        }, {
          label: 'Budget',
          data: chartData.budget,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.2)',
          tension: 0.4,
          fill: true
        }]
      },
      options: commonOptions
    })
  }

  // Comparison Chart
  if (comparisonChart.value) {
    charts.value.comparison = new Chart(comparisonChart.value, {
      type: 'bar',
      data: {
        labels: chartData.labels,
        datasets: [{
          label: 'Actual',
          data: chartData.actual,
          backgroundColor: 'rgba(139, 92, 246, 0.8)',
          borderRadius: 8
        }, {
          label: 'Budget',
          data: chartData.budget,
          backgroundColor: 'rgba(16, 185, 129, 0.8)',
          borderRadius: 8
        }]
      },
      options: commonOptions
    })
  }

  // Pie Chart
  if (pieChart.value) {
    charts.value.pie = new Chart(pieChart.value, {
      type: 'doughnut',
      data: {
        labels: chartData.labels.slice(0, 6),
        datasets: [{
          data: chartData.actual.slice(0, 6),
          backgroundColor: ['#8b5cf6', '#ec4899', '#10b981', '#f59e0b', '#3b82f6', '#ef4444']
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: { legend: { labels: { color: '#a78bfa' } } }
      }
    })
  }

  // Radar Chart
  if (radarChart.value) {
    charts.value.radar = new Chart(radarChart.value, {
      type: 'radar',
      data: {
        labels: chartData.labels.slice(0, 6),
        datasets: [{
          label: 'Performance',
          data: chartData.actual.slice(0, 6),
          borderColor: '#8b5cf6',
          backgroundColor: 'rgba(139, 92, 246, 0.2)'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: { legend: { labels: { color: '#a78bfa' } } },
        scales: { r: { ticks: { color: '#a78bfa' }, grid: { color: 'rgba(255,255,255,0.1)' } } }
      }
    })
  }

  // Polar Chart
  if (polarChart.value) {
    charts.value.polar = new Chart(polarChart.value, {
      type: 'polarArea',
      data: {
        labels: chartData.labels.slice(0, 6),
        datasets: [{
          data: chartData.actual.slice(0, 6),
          backgroundColor: [
            'rgba(139, 92, 246, 0.7)',
            'rgba(236, 72, 153, 0.7)',
            'rgba(16, 185, 129, 0.7)',
            'rgba(245, 158, 11, 0.7)',
            'rgba(59, 130, 246, 0.7)',
            'rgba(239, 68, 68, 0.7)'
          ]
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: { legend: { labels: { color: '#a78bfa' } } },
        scales: { r: { ticks: { color: '#a78bfa' }, grid: { color: 'rgba(255,255,255,0.1)' } } }
      }
    })
  }
}

const resetDashboard = () => {
  Object.values(charts.value).forEach(chart => chart?.destroy())
  charts.value = {}
  data.value = null
  selectedKpis.value = []
}

onBeforeUnmount(() => {
  Object.values(charts.value).forEach(chart => chart?.destroy())
})
</script>

<style scoped>
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(-50px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes shimmer {
  0% { background-position: -1000px 0; }
  100% { background-position: 1000px 0; }
}

.fade-in-up {
  animation: fadeInUp 0.6s ease-out forwards;
}

.slide-in {
  animation: slideIn 0.6s ease-out forwards;
}

.pulse-animation {
  animation: pulse 2s ease-in-out infinite;
}

.shimmer {
  background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 75%);
  background-size: 1000px 100%;
  animation: shimmer 2s infinite;
}

.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
}

.gradient-text {
  background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.kpi-card {
  transition: all 0.3s ease;
}

.kpi-card:hover {
  transform: translateY(-5px) scale(1.02);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.upload-zone {
  transition: all 0.3s ease;
}

.upload-zone:hover {
  transform: scale(1.02);
  border-color: rgba(139, 92, 246, 0.6);
}
</style>
