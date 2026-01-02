import { useEffect, useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Switch,
  TextField,
  Grid,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from '@mui/material'
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  PlayArrow as PlayIcon,
  Schedule as ScheduleIcon,
  Sync as SyncIcon,
} from '@mui/icons-material'
import { serversAPI, schedulesAPI, schedulerAPI } from '../services/api'
import { Server, Schedule } from '../types'

export default function Schedules() {
  const [servers, setServers] = useState<Server[]>([])
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingSchedule, setEditingSchedule] = useState<Schedule | null>(null)
  const [triggeringCheck, setTriggeringCheck] = useState(false)

  const [formData, setFormData] = useState({
    server_id: 0,
    enabled: true,
    schedule_type: 'weekly' as 'daily' | 'weekly' | 'monthly',
    day_of_week: 0,
    day_of_month: 1,
    hour: 3,
    minute: 0,
    update_type: 'all' as 'all' | 'security',
    auto_reboot: false,
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [serversRes, schedulesRes] = await Promise.all([
        serversAPI.getAll(),
        schedulesAPI.getAll(),
      ])
      setServers(serversRes.data)
      setSchedules(schedulesRes.data)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors du chargement')
    } finally {
      setLoading(false)
    }
  }

  const handleAutoCheckToggle = async (server: Server) => {
    try {
      await serversAPI.updateAutoCheck(
        server.id,
        !server.auto_check,
        server.check_interval
      )
      setSuccess(`Vérification automatique ${!server.auto_check ? 'activée' : 'désactivée'} pour ${server.name}`)
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors de la mise à jour')
    }
  }

  const handleIntervalChange = async (server: Server, interval: number) => {
    if (interval < 1 || interval > 168) return // Min 1h, Max 1 semaine

    try {
      await serversAPI.updateAutoCheck(server.id, server.auto_check, interval)
      setSuccess(`Intervalle mis à jour pour ${server.name}`)
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors de la mise à jour')
    }
  }

  const handleTriggerNow = async () => {
    try {
      setTriggeringCheck(true)
      await schedulerAPI.triggerNow()
      setSuccess('Vérification déclenchée pour tous les serveurs')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors du déclenchement')
    } finally {
      setTriggeringCheck(false)
    }
  }

  const handleAddSchedule = () => {
    setEditingSchedule(null)
    setFormData({
      server_id: servers[0]?.id || 0,
      enabled: true,
      schedule_type: 'weekly',
      day_of_week: 0,
      day_of_month: 1,
      hour: 3,
      minute: 0,
      update_type: 'all',
      auto_reboot: false,
    })
    setDialogOpen(true)
  }

  const handleEditSchedule = (schedule: Schedule) => {
    setEditingSchedule(schedule)
    setFormData({
      server_id: schedule.server_id,
      enabled: schedule.enabled,
      schedule_type: schedule.schedule_type,
      day_of_week: schedule.day_of_week || 0,
      day_of_month: schedule.day_of_month || 1,
      hour: schedule.hour,
      minute: schedule.minute,
      update_type: schedule.update_type,
      auto_reboot: schedule.auto_reboot,
    })
    setDialogOpen(true)
  }

  const handleSaveSchedule = async () => {
    try {
      if (editingSchedule) {
        await schedulesAPI.update(editingSchedule.id, formData)
        setSuccess('Planification mise à jour')
      } else {
        await schedulesAPI.create(formData.server_id, formData)
        setSuccess('Planification créée')
      }
      setDialogOpen(false)
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors de la sauvegarde')
    }
  }

  const handleDeleteSchedule = async (id: number) => {
    if (!confirm('Supprimer cette planification ?')) return

    try {
      await schedulesAPI.delete(id)
      setSuccess('Planification supprimée')
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors de la suppression')
    }
  }

  const getScheduleDescription = (schedule: Schedule) => {
    const time = `${String(schedule.hour).padStart(2, '0')}:${String(schedule.minute).padStart(2, '0')}`

    if (schedule.schedule_type === 'daily') {
      return `Tous les jours à ${time}`
    } else if (schedule.schedule_type === 'weekly') {
      const days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
      return `Tous les ${days[schedule.day_of_week || 0]} à ${time}`
    } else {
      return `Le ${schedule.day_of_month} de chaque mois à ${time}`
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
            Planifications
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Gérez les vérifications automatiques et les mises à jour planifiées
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={triggeringCheck ? <CircularProgress size={20} /> : <PlayIcon />}
          onClick={handleTriggerNow}
          disabled={triggeringCheck}
        >
          Vérifier maintenant
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess('')}>{success}</Alert>}

      {/* Auto-Check Configuration */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <SyncIcon sx={{ mr: 1 }} />
            <Typography variant="h6" fontWeight="bold">
              Vérification automatique
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Configurez la vérification automatique des mises à jour pour chaque serveur
          </Typography>

          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Serveur</TableCell>
                  <TableCell>Statut</TableCell>
                  <TableCell>MAJ disponibles</TableCell>
                  <TableCell>Intervalle (heures)</TableCell>
                  <TableCell>Auto-check</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {servers.map((server) => (
                  <TableRow key={server.id}>
                    <TableCell>
                      <Typography variant="body2" fontWeight="bold">
                        {server.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {server.hostname}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={server.status}
                        size="small"
                        color={
                          server.status === 'online' ? 'success' :
                          server.status === 'offline' ? 'error' :
                          server.status === 'updating' ? 'warning' : 'default'
                        }
                      />
                    </TableCell>
                    <TableCell>
                      {server.updates_available > 0 ? (
                        <Chip
                          label={server.updates_available}
                          size="small"
                          color="warning"
                        />
                      ) : (
                        <Chip label="0" size="small" color="success" variant="outlined" />
                      )}
                    </TableCell>
                    <TableCell>
                      <TextField
                        type="number"
                        value={server.check_interval}
                        onChange={(e) => handleIntervalChange(server, parseInt(e.target.value))}
                        size="small"
                        sx={{ width: 100 }}
                        inputProps={{ min: 1, max: 168 }}
                        disabled={!server.auto_check}
                      />
                    </TableCell>
                    <TableCell>
                      <Switch
                        checked={server.auto_check}
                        onChange={() => handleAutoCheckToggle(server)}
                        color="primary"
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Scheduled Updates */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <ScheduleIcon sx={{ mr: 1 }} />
              <Typography variant="h6" fontWeight="bold">
                Mises à jour planifiées
              </Typography>
            </Box>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleAddSchedule}
              disabled={servers.length === 0}
            >
              Nouvelle planification
            </Button>
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Planifiez l'application automatique des mises à jour
          </Typography>

          {schedules.length === 0 ? (
            <Alert severity="info">
              Aucune planification configurée. Créez-en une pour automatiser les mises à jour.
            </Alert>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Serveur</TableCell>
                    <TableCell>Planification</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Redémarrage auto</TableCell>
                    <TableCell>Statut</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {schedules.map((schedule) => (
                    <TableRow key={schedule.id}>
                      <TableCell>{schedule.server_name}</TableCell>
                      <TableCell>{getScheduleDescription(schedule)}</TableCell>
                      <TableCell>
                        <Chip
                          label={schedule.update_type === 'security' ? 'Sécurité' : 'Toutes'}
                          size="small"
                          color={schedule.update_type === 'security' ? 'error' : 'primary'}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        {schedule.auto_reboot ? 'Oui' : 'Non'}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={schedule.enabled ? 'Activé' : 'Désactivé'}
                          size="small"
                          color={schedule.enabled ? 'success' : 'default'}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Modifier">
                          <IconButton size="small" onClick={() => handleEditSchedule(schedule)}>
                            <EditIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Supprimer">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteSchedule(schedule.id)}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Schedule Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingSchedule ? 'Modifier la planification' : 'Nouvelle planification'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              select
              label="Serveur"
              value={formData.server_id}
              onChange={(e) => setFormData({ ...formData, server_id: parseInt(e.target.value) })}
              required
              fullWidth
            >
              {servers.map((server) => (
                <MenuItem key={server.id} value={server.id}>
                  {server.name} ({server.hostname})
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              label="Fréquence"
              value={formData.schedule_type}
              onChange={(e) => setFormData({ ...formData, schedule_type: e.target.value as any })}
              required
              fullWidth
            >
              <MenuItem value="daily">Quotidienne</MenuItem>
              <MenuItem value="weekly">Hebdomadaire</MenuItem>
              <MenuItem value="monthly">Mensuelle</MenuItem>
            </TextField>

            {formData.schedule_type === 'weekly' && (
              <TextField
                select
                label="Jour de la semaine"
                value={formData.day_of_week}
                onChange={(e) => setFormData({ ...formData, day_of_week: parseInt(e.target.value) })}
                required
                fullWidth
              >
                <MenuItem value={0}>Lundi</MenuItem>
                <MenuItem value={1}>Mardi</MenuItem>
                <MenuItem value={2}>Mercredi</MenuItem>
                <MenuItem value={3}>Jeudi</MenuItem>
                <MenuItem value={4}>Vendredi</MenuItem>
                <MenuItem value={5}>Samedi</MenuItem>
                <MenuItem value={6}>Dimanche</MenuItem>
              </TextField>
            )}

            {formData.schedule_type === 'monthly' && (
              <TextField
                type="number"
                label="Jour du mois"
                value={formData.day_of_month}
                onChange={(e) => setFormData({ ...formData, day_of_month: parseInt(e.target.value) })}
                required
                fullWidth
                inputProps={{ min: 1, max: 31 }}
                helperText="Jour du mois (1-31)"
              />
            )}

            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  type="number"
                  label="Heure"
                  value={formData.hour}
                  onChange={(e) => setFormData({ ...formData, hour: parseInt(e.target.value) })}
                  required
                  fullWidth
                  inputProps={{ min: 0, max: 23 }}
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  type="number"
                  label="Minute"
                  value={formData.minute}
                  onChange={(e) => setFormData({ ...formData, minute: parseInt(e.target.value) })}
                  required
                  fullWidth
                  inputProps={{ min: 0, max: 59 }}
                />
              </Grid>
            </Grid>

            <TextField
              select
              label="Type de mises à jour"
              value={formData.update_type}
              onChange={(e) => setFormData({ ...formData, update_type: e.target.value as any })}
              required
              fullWidth
            >
              <MenuItem value="all">Toutes les mises à jour</MenuItem>
              <MenuItem value="security">Mises à jour de sécurité uniquement</MenuItem>
            </TextField>

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.auto_reboot}
                  onChange={(e) => setFormData({ ...formData, auto_reboot: e.target.checked })}
                />
              }
              label="Redémarrer automatiquement si nécessaire"
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.enabled}
                  onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                />
              }
              label="Activer cette planification"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Annuler</Button>
          <Button onClick={handleSaveSchedule} variant="contained">
            {editingSchedule ? 'Modifier' : 'Créer'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
