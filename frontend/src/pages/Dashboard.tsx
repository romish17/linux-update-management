import { useEffect, useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material'
import {
  Storage as StorageIcon,
  Update as UpdateIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  CloudDone as CloudDoneIcon,
} from '@mui/icons-material'
import { statsAPI } from '../services/api'
import { Stats } from '../types'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      setLoading(true)
      const response = await statsAPI.get()
      setStats(response.data)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors du chargement des statistiques')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>
  }

  if (!stats) {
    return <Alert severity="info">Aucune donnée disponible</Alert>
  }

  const statCards = [
    {
      title: 'Total Serveurs',
      value: stats.total_servers,
      icon: <StorageIcon />,
      color: '#667eea',
    },
    {
      title: 'Mises à jour disponibles',
      value: stats.total_updates,
      icon: <UpdateIcon />,
      color: '#f59e0b',
    },
    {
      title: 'Serveurs en ligne',
      value: stats.servers_online,
      icon: <CheckCircleIcon />,
      color: '#10b981',
    },
    {
      title: 'Serveurs hors ligne',
      value: stats.servers_offline,
      icon: <ErrorIcon />,
      color: '#ef4444',
    },
    {
      title: 'Planifications actives',
      value: stats.enabled_schedules,
      icon: <ScheduleIcon />,
      color: '#8b5cf6',
    },
    {
      title: 'Mises à jour (24h)',
      value: stats.updates_last_24h,
      icon: <CloudDoneIcon />,
      color: '#06b6d4',
    },
  ]

  return (
    <Box>
      <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
        Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Vue d'ensemble de vos serveurs Linux
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        {statCards.map((card) => (
          <Grid item xs={12} sm={6} md={4} key={card.title}>
            <Card
              sx={{
                height: '100%',
                borderRadius: 2,
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 48,
                      height: 48,
                      borderRadius: 2,
                      bgcolor: `${card.color}20`,
                      color: card.color,
                      mr: 2,
                    }}
                  >
                    {card.icon}
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {card.title}
                  </Typography>
                </Box>
                <Typography variant="h3" fontWeight="bold">
                  {card.value}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" gutterBottom>
                Répartition OS
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Debian
                  </Typography>
                  <Typography variant="h4" fontWeight="bold" color="primary">
                    {stats.servers_debian}
                  </Typography>
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    AlmaLinux
                  </Typography>
                  <Typography variant="h4" fontWeight="bold" color="secondary">
                    {stats.servers_almalinux}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" gutterBottom>
                État des serveurs
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                <Chip
                  label={`${stats.servers_online} En ligne`}
                  color="success"
                  variant="outlined"
                  sx={{ flex: 1 }}
                />
                <Chip
                  label={`${stats.servers_updating} Mise à jour`}
                  color="warning"
                  variant="outlined"
                  sx={{ flex: 1 }}
                />
                <Chip
                  label={`${stats.servers_offline} Hors ligne`}
                  color="error"
                  variant="outlined"
                  sx={{ flex: 1 }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" gutterBottom>
                Activité récente
              </Typography>
              {stats.recent_activity.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                  Aucune activité récente
                </Typography>
              ) : (
                <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Serveur</TableCell>
                        <TableCell>Action</TableCell>
                        <TableCell>Statut</TableCell>
                        <TableCell>Date</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {stats.recent_activity.slice(0, 5).map((activity) => (
                        <TableRow key={activity.id}>
                          <TableCell>{activity.server_name}</TableCell>
                          <TableCell>
                            {activity.action === 'check' && 'Vérification des mises à jour'}
                            {activity.action === 'update' && 'Application des mises à jour'}
                            {activity.action === 'reboot' && 'Redémarrage'}
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={activity.status}
                              color={activity.status === 'success' ? 'success' : 'error'}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>
                            {format(new Date(activity.timestamp), 'Pp', { locale: fr })}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
