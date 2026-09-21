import { PageContainer, PageHeader, Card, CardBody } from '../components/ui'
import { color, font, space } from '../lib/tokens'
import { getAuth } from '../services/api'

const gridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
  gap: space[4],
}

const metricLabelStyle = {
  fontSize: font.size.caption,
  color: color.text.muted,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
  fontWeight: 600,
}

const metricValueStyle = {
  fontSize: font.size.sectionTitle,
  fontWeight: font.weight.semibold,
  color: color.text.primary,
  marginTop: space[1],
}

export default function DashboardPage() {
  const { activeTenantName } = getAuth()

  return (
    <PageContainer>
      <PageHeader
        title={activeTenantName ? `${activeTenantName} dashboard` : 'Dashboard'}
        description="Your accounting workspace overview."
      />

      <div style={gridStyle}>
        <Card>
          <CardBody>
            <div style={metricLabelStyle}>Getting started</div>
            <div style={metricValueStyle}>Welcome</div>
            <p style={{ fontSize: font.size.bodySmall, color: color.text.muted, marginTop: space[2] }}>
              Your accounting system is ready. Use the sidebar to navigate modules.
            </p>
          </CardBody>
        </Card>
      </div>
    </PageContainer>
  )
}
