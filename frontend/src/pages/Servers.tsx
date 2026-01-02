import { useEffect, useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  CardActions,
  Grid,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  IconButton,
  ToggleButtonGroup,
  ToggleButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tooltip,
  FormControlLabel,
  Switch,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material'
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Update as UpdateIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  ViewModule as GridViewIcon,
  ViewList as ListViewIcon,
  Sync as SyncIcon,
  Shield as ShieldIcon,
  VpnKey as VpnKeyIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  HourglassEmpty as PendingIcon,
  Loop as LoadingIcon,
} from '@mui/icons-material'
import { serversAPI } from '../services/api'
import { Server, ProvisioningStep } from '../types'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

type ViewMode = 'grid' | 'list'

export default function Servers() {
  const [servers, setServers] = useState<Server[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingServer, setEditingServer] = useState<Server | null>(null)
  const [useProvisioning, setUseProvisioning] = useState(false)
  const [isProvisioning, setIsProvisioning] = useState(false)
  const [provisioningSteps, setProvisioningSteps] = useState<ProvisioningStep[]>([])
  const [formData, setFormData] = useState({
    name: '',
    hostname: '',
    port: 22,
    username: '',
    ssh_key_path: '/app/data/ssh_keys/lum_rsa',
    os_type: 'debian' as 'debian' | 'almalinux',
    root_username: 'root',
    root_password: '',
  })

  useEffect(() => {
    loadServers()
  }, [])

  const loadServers = async () => {
    try {
      setLoading(true)
      const response = await serversAPI.getAll()
      setServers(response.data)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors du chargement des serveurs')
    } finally {
      setLoading(false)
    }
  }

  const handleAddServer = () => {
    setEditingServer(null)
    setUseProvisioning(false)
    setProvisioningSteps([])
    setFormData({
      name: '',
      hostname: '',
      port: 22,
      username: '',
      ssh_key_path: '/app/data/ssh_keys/lum_rsa',
      os_type: 'debian',
      root_username: 'root',
      root_password: '',
    })
    setDialogOpen(true)
  }

  const handleEditServer = (server: Server) => {
    setEditingServer(server)
    setFormData({
      name: server.name,
      hostname: server.hostname,
      port: server.port,
      username: server.username,
      ssh_key_path: server.ssh_key_path || '/root/.ssh/id_rsa',
      os_type: server.os_type,
    })
    setDialogOpen(true)
  }

  const handleSaveServer = async () => {
    try {
      if (editingServer) {
        // Editing existing server - no provisioning
        await serversAPI.update(editingServer.id, formData)
        setDialogOpen(false)
        loadServers()
      } else if (useProvisioning) {
        // Provisioning new server
        setIsProvisioning(true)
        setProvisioningSteps([])

        const response = await serversAPI.provision({
          name: formData.name,
          hostname: formData.hostname,
          port: formData.port,
          root_username: formData.root_username,
          root_password: formData.root_password,
          os_type: formData.os_type,
        })

        if (response.data.success) {
          setProvisioningSteps(response.data.provisioning_steps || [])
          setTimeout(() => {
            setDialogOpen(false)
            setIsProvisioning(false)
            loadServers()
          }, 2000)
        } else {
          setProvisioningSteps(response.data.provisioning_steps || [])
          setError(response.data.error || 'Provisioning failed')
          setIsProvisioning(false)
        }
      } else {
        // Manual server creation
        await serversAPI.create({
          name: formData.name,
          hostname: formData.hostname,
          port: formData.port,
          username: formData.username,
          ssh_key_path: formData.ssh_key_path,
          os_type: formData.os_type,
        })
        setDialogOpen(false)
        loadServers()
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors de la sauvegarde')
      setIsProvisioning(false)
      if (err.response?.data?.steps) {
        setProvisioningSteps(err.response.data.steps)
      }
    }
  }

  const handleDeleteServer = async (id: number) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce serveur ?')) return
    try {
      await serversAPI.delete(id)
      loadServers()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors de la suppression')
    }
  }

  const handleCheckUpdates = async (id: number, securityOnly: boolean = false) => {
    try {
      await serversAPI.checkUpdates(id, securityOnly)
      loadServers()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors de la vérification')
    }
  }

  const handleApplyUpdates = async (id: number, securityOnly: boolean = false, autoReboot: boolean = false) => {
    if (!confirm('Êtes-vous sûr de vouloir appliquer les mises à jour ?')) return
    try {
      await serversAPI.applyUpdates(id, securityOnly, autoReboot)
      loadServers()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors de la mise à jour')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'success'
      case 'offline':
        return 'error'
      case 'updating':
        return 'warning'
      default:
        return 'default'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'online':
        return 'En ligne'
      case 'offline':
        return 'Hors ligne'
      case 'updating':
        return 'Mise à jour'
      default:
        return 'Inconnu'
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
            Serveurs
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Gérez vos serveurs Linux
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={(_, value) => value && setViewMode(value)}
            size="small"
          >
            <ToggleButton value="grid">
              <GridViewIcon />
            </ToggleButton>
            <ToggleButton value="list">
              <ListViewIcon />
            </ToggleButton>
          </ToggleButtonGroup>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadServers}
          >
            Actualiser
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleAddServer}
          >
            Ajouter un serveur
          </Button>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {viewMode === 'grid' ? (
        <Grid container spacing={3}>
          {servers.map((server) => (
            <Grid item xs={12} sm={6} md={4} key={server.id}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 2 }}>
                    <Typography variant="h6" fontWeight="bold">
                      {server.name}
                    </Typography>
                    <Chip
                      label={getStatusLabel(server.status)}
                      color={getStatusColor(server.status)}
                      size="small"
                    />
                  </Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {server.hostname}:{server.port}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    User: {server.username}
                  </Typography>
                  <Chip
                    label={server.os_type}
                    size="small"
                    variant="outlined"
                    sx={{ mt: 1 }}
                  />
                  {server.updates_available > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Chip
                        label={`${server.updates_available} mises à jour disponibles`}
                        color="warning"
                        size="small"
                      />
                    </Box>
                  )}
                  {server.last_check && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                      Dernière vérification: {format(new Date(server.last_check), 'Pp', { locale: fr })}
                    </Typography>
                  )}
                </CardContent>
                <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
                  <Box>
                    <Tooltip title="Vérifier les mises à jour">
                      <IconButton
                        size="small"
                        onClick={() => handleCheckUpdates(server.id)}
                        disabled={server.status === 'updating'}
                      >
                        <SyncIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Mises à jour de sécurité">
                      <IconButton
                        size="small"
                        onClick={() => handleCheckUpdates(server.id, true)}
                        disabled={server.status === 'updating'}
                      >
                        <ShieldIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Appliquer les mises à jour">
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => handleApplyUpdates(server.id)}
                        disabled={server.status === 'updating' || server.updates_available === 0}
                      >
                        <UpdateIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                  <Box>
                    <Tooltip title="Modifier">
                      <IconButton size="small" onClick={() => handleEditServer(server)}>
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Supprimer">
                      <IconButton size="small" color="error" onClick={() => handleDeleteServer(server.id)}>
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Nom</TableCell>
                <TableCell>Hostname</TableCell>
                <TableCell>OS</TableCell>
                <TableCell>Statut</TableCell>
                <TableCell>Mises à jour</TableCell>
                <TableCell>Dernière vérification</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {servers.map((server) => (
                <TableRow key={server.id}>
                  <TableCell>{server.name}</TableCell>
                  <TableCell>{server.hostname}:{server.port}</TableCell>
                  <TableCell>
                    <Chip label={server.os_type} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={getStatusLabel(server.status)}
                      color={getStatusColor(server.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {server.updates_available > 0 ? (
                      <Chip
                        label={server.updates_available}
                        color="warning"
                        size="small"
                      />
                    ) : (
                      '0'
                    )}
                  </TableCell>
                  <TableCell>
                    {server.last_check
                      ? format(new Date(server.last_check), 'Pp', { locale: fr })
                      : '-'}
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="Vérifier">
                      <IconButton
                        size="small"
                        onClick={() => handleCheckUpdates(server.id)}
                        disabled={server.status === 'updating'}
                      >
                        <SyncIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Appliquer">
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => handleApplyUpdates(server.id)}
                        disabled={server.status === 'updating' || server.updates_available === 0}
                      >
                        <UpdateIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Modifier">
                      <IconButton size="small" onClick={() => handleEditServer(server)}>
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Supprimer">
                      <IconButton size="small" color="error" onClick={() => handleDeleteServer(server.id)}>
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

      <Dialog open={dialogOpen} onClose={() => !isProvisioning && setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingServer ? 'Modifier le serveur' : 'Ajouter un serveur'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            {/* Provisioning Toggle - Only for new servers */}
            {!editingServer && (
              <FormControlLabel
                control={
                  <Switch
                    checked={useProvisioning}
                    onChange={(e) => setUseProvisioning(e.target.checked)}
                    disabled={isProvisioning}
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <VpnKeyIcon />
                    <Typography>Provisioning automatique (créer l'utilisateur et déployer la clé SSH)</Typography>
                  </Box>
                }
              />
            )}

            {/* Common Fields */}
            <TextField
              label="Nom"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              fullWidth
              disabled={isProvisioning}
            />
            <TextField
              label="Hostname / IP"
              value={formData.hostname}
              onChange={(e) => setFormData({ ...formData, hostname: e.target.value })}
              required
              fullWidth
              disabled={isProvisioning}
            />
            <TextField
              label="Port SSH"
              type="number"
              value={formData.port}
              onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
              required
              fullWidth
              disabled={isProvisioning}
            />
            <TextField
              select
              label="Type OS"
              value={formData.os_type}
              onChange={(e) => setFormData({ ...formData, os_type: e.target.value as 'debian' | 'almalinux' })}
              required
              fullWidth
              disabled={isProvisioning}
            >
              <MenuItem value="debian">Debian / Ubuntu</MenuItem>
              <MenuItem value="almalinux">AlmaLinux / RHEL / CentOS</MenuItem>
            </TextField>

            {/* Provisioning Fields */}
            {useProvisioning && !editingServer ? (
              <>
                <Alert severity="info" sx={{ mt: 1 }}>
                  Le provisioning va créer automatiquement l'utilisateur <strong>lum-user</strong> sur le serveur distant
                  et déployer la clé SSH de l'application.
                </Alert>
                <TextField
                  label="Utilisateur root / sudo"
                  value={formData.root_username}
                  onChange={(e) => setFormData({ ...formData, root_username: e.target.value })}
                  required
                  fullWidth
                  disabled={isProvisioning}
                  helperText="Utilisateur avec privilèges root (généralement 'root')"
                />
                <TextField
                  label="Mot de passe root"
                  type="password"
                  value={formData.root_password}
                  onChange={(e) => setFormData({ ...formData, root_password: e.target.value })}
                  required
                  fullWidth
                  disabled={isProvisioning}
                  helperText="Mot de passe temporaire (ne sera pas stocké)"
                />
              </>
            ) : (
              <>
                {/* Manual Configuration Fields */}
                <TextField
                  label="Utilisateur SSH"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  required
                  fullWidth
                  disabled={isProvisioning}
                  helperText="Utilisateur SSH déjà configuré sur le serveur"
                />
                <TextField
                  label="Chemin clé SSH"
                  value={formData.ssh_key_path}
                  onChange={(e) => setFormData({ ...formData, ssh_key_path: e.target.value })}
                  fullWidth
                  disabled={isProvisioning}
                  helperText="Chemin vers la clé SSH privée"
                />
              </>
            )}

            {/* Provisioning Progress */}
            {isProvisioning && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Provisioning en cours...
                </Typography>
                <LinearProgress sx={{ mb: 2 }} />
                <List dense>
                  {provisioningSteps.map((step, index) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        {step.status === 'success' && <CheckCircleIcon color="success" />}
                        {step.status === 'failed' && <ErrorIcon color="error" />}
                        {step.status === 'running' && <LoadingIcon color="primary" className="rotating" />}
                        {step.status === 'pending' && <PendingIcon color="disabled" />}
                      </ListItemIcon>
                      <ListItemText
                        primary={step.message || step.name}
                        secondary={step.error}
                        secondaryTypographyProps={{ color: 'error' }}
                      />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} disabled={isProvisioning}>
            Annuler
          </Button>
          <Button
            onClick={handleSaveServer}
            variant="contained"
            disabled={isProvisioning}
            startIcon={useProvisioning && !editingServer ? <VpnKeyIcon /> : null}
          >
            {isProvisioning ? 'Provisioning...' : editingServer ? 'Modifier' : useProvisioning ? 'Provisionner' : 'Ajouter'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
