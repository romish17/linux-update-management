import { useEffect, useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  MenuItem,
  Grid,
  IconButton,
  Collapse,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
} from '@mui/icons-material'
import { historyAPI } from '../services/api'
import { UpdateHistory } from '../types'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

export default function History() {
  const [history, setHistory] = useState<UpdateHistory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filterAction, setFilterAction] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    try {
      setLoading(true)
      const response = await historyAPI.getAll()
      setHistory(response.data)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors du chargement de l\'historique')
    } finally {
      setLoading(false)
    }
  }

  const toggleRow = (id: number) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedRows(newExpanded)
  }

  const filteredHistory = history.filter((item) => {
    if (filterAction !== 'all' && item.action !== filterAction) return false
    if (filterStatus !== 'all') {
      const status = item.success ? 'success' : 'error'
      if (status !== filterStatus) return false
    }
    return true
  })

  const getActionLabel = (action: string) => {
    switch (action) {
      case 'check':
        return 'Vérification'
      case 'update':
        return 'Mise à jour'
      case 'reboot':
        return 'Redémarrage'
      default:
        return action
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon color="success" />
      case 'error':
        return <ErrorIcon color="error" />
      default:
        return <InfoIcon color="info" />
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
      <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
        Historique
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Historique des mises à jour et actions
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                fullWidth
                label="Filtrer par action"
                value={filterAction}
                onChange={(e) => setFilterAction(e.target.value)}
                size="small"
              >
                <MenuItem value="all">Toutes les actions</MenuItem>
                <MenuItem value="check">Vérification</MenuItem>
                <MenuItem value="update">Mise à jour</MenuItem>
                <MenuItem value="reboot">Redémarrage</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                fullWidth
                label="Filtrer par statut"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                size="small"
              >
                <MenuItem value="all">Tous les statuts</MenuItem>
                <MenuItem value="success">Succès</MenuItem>
                <MenuItem value="error">Erreur</MenuItem>
              </TextField>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell width={50}></TableCell>
              <TableCell>Serveur</TableCell>
              <TableCell>Action</TableCell>
              <TableCell>Statut</TableCell>
              <TableCell>Date</TableCell>
              <TableCell>Durée</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredHistory.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                    Aucun historique disponible
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredHistory.map((item) => (
                <>
                  <TableRow key={item.id} hover>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() => toggleRow(item.id)}
                        sx={{
                          transform: expandedRows.has(item.id) ? 'rotate(180deg)' : 'rotate(0deg)',
                          transition: 'transform 0.3s',
                        }}
                      >
                        <ExpandMoreIcon />
                      </IconButton>
                    </TableCell>
                    <TableCell>{item.server_name}</TableCell>
                    <TableCell>
                      <Chip
                        label={getActionLabel(item.action)}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {getStatusIcon(item.success ? 'success' : 'error')}
                        <Chip
                          label={item.success ? 'Succès' : 'Erreur'}
                          color={item.success ? 'success' : 'error'}
                          size="small"
                        />
                      </Box>
                    </TableCell>
                    <TableCell>
                      {format(new Date(item.created_at), 'Pp', { locale: fr })}
                    </TableCell>
                    <TableCell>
                      {item.duration ? `${item.duration.toFixed(2)}s` : '-'}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell colSpan={6} sx={{ py: 0, border: 0 }}>
                      <Collapse in={expandedRows.has(item.id)} timeout="auto" unmountOnExit>
                        <Box sx={{ p: 2, bgcolor: 'background.default' }}>
                          <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                            Détails
                          </Typography>
                          {item.packages_count > 0 && (
                            <Typography variant="body2" color="text.secondary" gutterBottom>
                              Paquets: {item.packages_count}
                            </Typography>
                          )}
                          {item.update_type === 'security' && (
                            <Chip
                              label="Sécurité uniquement"
                              color="warning"
                              size="small"
                              sx={{ mb: 1 }}
                            />
                          )}
                          {item.output && (
                            <>
                              <Typography variant="subtitle2" fontWeight="bold" sx={{ mt: 2, mb: 1 }}>
                                Logs
                              </Typography>
                              <Paper
                                variant="outlined"
                                sx={{
                                  p: 2,
                                  bgcolor: '#1e1e1e',
                                  color: '#d4d4d4',
                                  fontFamily: 'monospace',
                                  fontSize: '0.875rem',
                                  maxHeight: 300,
                                  overflow: 'auto',
                                }}
                              >
                                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                                  {item.output}
                                </pre>
                              </Paper>
                            </>
                          )}
                        </Box>
                      </Collapse>
                    </TableCell>
                  </TableRow>
                </>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}
