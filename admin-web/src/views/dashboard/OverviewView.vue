<template>
  <div class="page-stack">
    <ElAlert
      v-if="dashboardError"
      class="page-alert"
      type="error"
      :closable="false"
      :title="dashboardError"
    />

    <div v-if="dashboardLoading" class="skeleton-grid">
      <ElSkeleton v-for="index in 4" :key="index" animated>
        <template #template>
          <div class="skeleton-card"></div>
        </template>
      </ElSkeleton>
    </div>

    <template v-else-if="dashboard">
      <section class="hero-grid">
        <article class="hero-card hero-card--accent">
          <div class="hero-card__head">
            <span>合同执行率</span>
            <ElTag type="success" round>{{ dashboard.metric_version }}</ElTag>
          </div>
          <strong>{{ formatPercent(dashboard.contract_execution_rate) }}</strong>
          <p>仅统计执行阶段合同</p>
        </article>

        <article class="hero-card hero-card--warm">
          <div class="hero-card__head">
            <span>当日实收</span>
            <span class="hero-card__status">{{ dashboard.sla_status }}</span>
          </div>
          <strong>¥{{ formatMoney(dashboard.actual_receipt_today) }}</strong>
          <p>按上海自然日统计</p>
        </article>

        <article class="hero-card hero-card--deep">
          <div class="hero-card__head">
            <span>当日实付</span>
            <span class="hero-card__status">库存联动</span>
          </div>
          <strong>¥{{ formatMoney(dashboard.actual_payment_today) }}</strong>
          <p>以已确认/已核销净额计算</p>
        </article>

        <article class="hero-card hero-card--alert">
          <div class="hero-card__head">
            <span>超阈值告警数</span>
            <span class="hero-card__status">需处理</span>
          </div>
          <strong>{{ dashboard.threshold_alert_count }}</strong>
          <p>点击左侧导航进入业务看板处理</p>
        </article>
      </section>

      <section class="panel-grid">
        <article class="panel-card panel-card--wide">
          <header class="panel-card__header">
            <div>
              <p class="panel-card__eyebrow">异常分布</p>
              <h3>经营风险一屏可见</h3>
            </div>
            <span>{{ formatDateTime(boardSnapshotTime) }}</span>
          </header>
          <div class="distribution-list">
            <div v-for="item in anomalyDistribution" :key="item.key" class="distribution-row">
              <div class="distribution-row__meta">
                <strong>{{ item.label }}</strong>
                <span>{{ item.value }} 项</span>
              </div>
              <div class="distribution-row__track">
                <div class="distribution-row__bar" :style="{ width: `${Math.max(item.ratio * 100, 6)}%` }"></div>
              </div>
            </div>
          </div>
        </article>

        <article class="panel-card">
          <header class="panel-card__header">
            <div>
              <p class="panel-card__eyebrow">今日执行摘要</p>
              <h3>库存与履约同步观察</h3>
            </div>
            <span>{{ dashboard.sla_status }}</span>
          </header>
          <div class="summary-grid">
            <div class="summary-tile">
              <span>库存周转</span>
              <strong>{{ dashboard.inventory_turnover_30d }}</strong>
            </div>
            <div class="summary-tile">
              <span>快照时间</span>
              <strong>{{ formatDateTime(dashboard.snapshot_time) }}</strong>
            </div>
            <div class="summary-tile">
              <span>今日实收</span>
              <strong>¥{{ formatMoney(dashboard.actual_receipt_today) }}</strong>
            </div>
            <div class="summary-tile">
              <span>今日实付</span>
              <strong>¥{{ formatMoney(dashboard.actual_payment_today) }}</strong>
            </div>
            <div class="summary-tile">
              <span>履约滞留</span>
              <strong>{{ board?.fulfillment_stagnant_count ?? 0 }} 项</strong>
            </div>
          </div>
        </article>
      </section>

      <section class="shortcut-row">
        <ElButton type="primary" round>查看业务看板</ElButton>
        <ElButton plain round>查看合同详情链路</ElButton>
        <ElButton plain round>查看收付款单列表</ElButton>
      </section>
    </template>

    <ElEmpty v-else description="暂无仪表盘数据" />
  </div>
</template>

<script setup lang="ts">
import { ElAlert, ElButton, ElEmpty, ElSkeleton, ElTag } from 'element-plus'
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'

import { useReportStore } from '@/stores/report'
import { formatDateTime, formatMoney, formatPercent } from '@/utils/formatters'

const reportStore = useReportStore()
const { anomalyDistribution, board, dashboard, boardError, boardLoading, dashboardError, dashboardLoading } = storeToRefs(reportStore)

const boardSnapshotTime = computed(() => board.value?.snapshot_time ?? dashboard.value?.snapshot_time ?? null)

onMounted(async () => {
  if (!dashboard.value && !dashboardLoading.value) {
    await reportStore.loadDashboard()
  }
  if (!board.value && !boardLoading.value && !boardError.value) {
    await reportStore.loadBoard()
  }
})
</script>
