import { useEffect, useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Paper,
  Grid,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  Divider,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  VpnKey as VpnKeyIcon,
  Refresh as RefreshIcon,
  ContentCopy as CopyIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material'
import { sshKeyAPI } from '../services/api'
import { SSHKeyInfo } from '../types'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

export default function Settings() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [keyInfo, setKeyInfo] = useState<SSHKeyInfo | null>(null)
  const [regenerateDialogOpen, setRegenerateDialogOpen] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    loadKeyInfo()
  }, [])

  const loadKeyInfo = async () => {
    try {
      setLoading(true)
      const response = await sshKeyAPI.getInfo()
      setKeyInfo(response.data)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors du chargement des informations')
    } finally {
      setLoading(false)
    }
  }

  const handleCopyPublicKey = async () => {
    if (keyInfo?.public_key) {
      try {
        await navigator.clipboard.writeText(keyInfo.public_key)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      } catch (err) {
        setError('Erreur lors de la copie dans le presse-papier')
      }
    }
  }

  const handleRegenerateKey = async () => {
    try {
      setRegenerating(true)
      setError('')
      setSuccess('')

      const response = await sshKeyAPI.regenerate()

      if (response.data.success) {
        setSuccess('Clé SSH régénérée avec succès')
        setRegenerateDialogOpen(false)
        loadKeyInfo()
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors de la régénération de la clé')
    } finally {
      setRegenerating(false)
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
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
          Paramètres
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Configuration de la clé SSH pour le provisioning automatique
        </Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess('')}>{success}</Alert>}

      <Grid container spacing={3}>
        {/* SSH Key Information Card */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <VpnKeyIcon sx={{ mr: 1, fontSize: 28 }} />
                <Typography variant="h6" fontWeight="bold">
                  Clé SSH de Provisioning
                </Typography>
              </Box>

              <Divider sx={{ mb: 2 }} />

              {!keyInfo?.exists ? (
                <Alert severity="info">
                  Aucune clé SSH générée. La clé sera créée automatiquement lors du premier provisioning.
                </Alert>
              ) : (
                <Box>
                  {/* Key Status */}
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Statut
                    </Typography>
                    <Chip
                      icon={<CheckCircleIcon />}
                      label="Clé active"
                      color="success"
                      size="small"
                    />
                  </Box>

                  {/* Key Paths */}
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Emplacement
                    </Typography>
                    <Paper sx={{ p: 2, bgcolor: 'grey.50' }} variant="outlined">
                      <Typography variant="body2" fontFamily="monospace" sx={{ mb: 1 }}>
                        <strong>Clé privée:</strong> {keyInfo.private_key_path}
                      </Typography>
                      <Typography variant="body2" fontFamily="monospace">
                        <strong>Clé publique:</strong> {keyInfo.public_key_path}
                      </Typography>
                    </Paper>
                  </Box>

                  {/* Key Fingerprint */}
                  {keyInfo.fingerprint && (
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        Empreinte
                      </Typography>
                      <Paper sx={{ p: 2, bgcolor: 'grey.50' }} variant="outlined">
                        <Typography variant="body2" fontFamily="monospace">
                          {keyInfo.fingerprint}
                        </Typography>
                      </Paper>
                    </Box>
                  )}

                  {/* Creation Date */}
                  {keyInfo.created && (
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        Date de création
                      </Typography>
                      <Typography variant="body2">
                        {format(new Date(keyInfo.created * 1000), 'PPpp', { locale: fr })}
                      </Typography>
                    </Box>
                  )}

                  {/* Public Key Display */}
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="subtitle2" color="text.secondary">
                        Clé publique
                      </Typography>
                      <Tooltip title={copied ? "Copié !" : "Copier la clé publique"}>
                        <IconButton size="small" onClick={handleCopyPublicKey}>
                          {copied ? <CheckCircleIcon color="success" /> : <CopyIcon />}
                        </IconButton>
                      </Tooltip>
                    </Box>
                    <Paper sx={{ p: 2, bgcolor: 'grey.50', maxHeight: 150, overflow: 'auto' }} variant="outlined">
                      <Typography
                        variant="body2"
                        fontFamily="monospace"
                        sx={{ wordBreak: 'break-all', fontSize: '0.75rem' }}
                      >
                        {keyInfo.public_key}
                      </Typography>
                    </Paper>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      Utilisez cette clé pour déployer manuellement l'accès sur vos serveurs si nécessaire
                    </Typography>
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Actions Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" gutterBottom>
                Actions
              </Typography>

              <Divider sx={{ mb: 2 }} />

              <Button
                variant="outlined"
                color="warning"
                startIcon={<RefreshIcon />}
                fullWidth
                onClick={() => setRegenerateDialogOpen(true)}
                disabled={!keyInfo?.exists}
                sx={{ mb: 2 }}
              >
                Régénérer la clé
              </Button>

              <Alert severity="warning" icon={<WarningIcon />}>
                <Typography variant="body2" fontWeight="bold" gutterBottom>
                  ⚠️ Attention
                </Typography>
                <Typography variant="caption">
                  La régénération de la clé SSH invalidera l'accès à tous les serveurs provisionnés avec l'ancienne clé.
                  Vous devrez re-provisionner tous vos serveurs existants.
                </Typography>
              </Alert>
            </CardContent>
          </Card>

          {/* Information Card */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" gutterBottom>
                À propos
              </Typography>

              <Divider sx={{ mb: 2 }} />

              <Typography variant="body2" color="text.secondary" paragraph>
                Cette clé SSH est utilisée automatiquement lors du provisioning des serveurs.
              </Typography>

              <Typography variant="body2" color="text.secondary" paragraph>
                L'utilisateur <strong>lum-user</strong> est créé sur chaque serveur provisionné avec cette clé.
              </Typography>

              <Typography variant="body2" color="text.secondary">
                La clé est stockée de manière sécurisée dans le conteneur backend et n'est jamais exposée aux clients.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Regenerate Confirmation Dialog */}
      <Dialog
        open={regenerateDialogOpen}
        onClose={() => !regenerating && setRegenerateDialogOpen(false)}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon color="warning" />
          Régénérer la clé SSH ?
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            Cette action va générer une nouvelle paire de clés SSH et <strong>rendre inaccessibles tous les serveurs
            actuellement provisionnés</strong> avec l'ancienne clé.
          </DialogContentText>
          <DialogContentText sx={{ mt: 2 }}>
            Vous devrez :
          </DialogContentText>
          <Box component="ul" sx={{ mt: 1 }}>
            <li>
              <DialogContentText>
                Soit re-provisionner chaque serveur (avec les identifiants root)
              </DialogContentText>
            </li>
            <li>
              <DialogContentText>
                Soit déployer manuellement la nouvelle clé publique sur chaque serveur
              </DialogContentText>
            </li>
          </Box>
          <DialogContentText sx={{ mt: 2, fontWeight: 'bold' }}>
            Êtes-vous sûr de vouloir continuer ?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRegenerateDialogOpen(false)} disabled={regenerating}>
            Annuler
          </Button>
          <Button
            onClick={handleRegenerateKey}
            color="warning"
            variant="contained"
            disabled={regenerating}
            startIcon={regenerating ? <CircularProgress size={16} /> : <RefreshIcon />}
          >
            {regenerating ? 'Régénération...' : 'Régénérer'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
