import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const ok = (data, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  statusText: String(status),
  json: async () => data,
})

describe('api client', () => {
  let api
  let fetchMock

  async function loadApi(cookie = '') {
    document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT'
    if (cookie) document.cookie = cookie
    vi.resetModules()
    api = await import('./api.js')
    return api
  }

  beforeEach(() => {
    fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    document.cookie = ''
  })

  it('sends JSON body with CSRF token for POST', async () => {
    await loadApi('csrftoken=tok123')
    fetchMock.mockResolvedValue(ok({ user: { username: 'a' }, csrfToken: 'tok123' }))

    await api.login({ username: 'a', password: 'p' })

    const [url, opts] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/auth/login/')
    expect(opts.method).toBe('POST')
    expect(opts.headers['X-CSRFToken']).toBe('tok123')
    expect(opts.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(opts.body)).toEqual({ username: 'a', password: 'p' })
  })

  it('does not attach CSRF header to GET', async () => {
    await loadApi('csrftoken=tok123')
    fetchMock.mockResolvedValue(ok({ rooms: [] }))

    await api.listRooms()

    const [, opts] = fetchMock.mock.calls[0]
    expect(opts.method).toBe('GET')
    expect(opts.headers['X-CSRFToken']).toBeUndefined()
  })

  it('fetches a CSRF token first when the cookie is missing', async () => {
    await loadApi('')
    fetchMock
      .mockResolvedValueOnce(ok({ csrfToken: 'fresh' }))
      .mockResolvedValueOnce(ok({ ok: true }))

    await api.joinRoom(1)

    const urls = fetchMock.mock.calls.map(([url]) => url)
    expect(urls[0]).toBe('/api/auth/csrf/')
    expect(urls[1]).toBe('/api/rooms/1/join/')
    const [, opts] = fetchMock.mock.calls[1]
    expect(opts.headers['X-CSRFToken']).toBe('fresh')
  })

  it('retries once with a fresh token after a CSRF rejection', async () => {
    await loadApi('csrftoken=stale')
    fetchMock
      .mockResolvedValueOnce(ok({ detail: 'CSRF Failed' }, 403))
      .mockResolvedValueOnce(ok({ csrfToken: 'fresh' }))
      .mockResolvedValueOnce(ok({ user: { username: 'a' }, csrfToken: 'rotated' }))

    await api.login({ username: 'a', password: 'p' })

    const sent = fetchMock.mock.calls
      .filter(([url]) => url !== '/api/auth/csrf/')
      .map(([, opts]) => opts.headers['X-CSRFToken'])
    expect(sent).toEqual(['stale', 'fresh'])
  })

  it('cannot retry twice (guards against loops)', async () => {
    await loadApi('csrftoken=bad')
    fetchMock.mockImplementation((url) =>
      url === '/api/auth/csrf/' ? ok({ csrfToken: 'fresh' }) : ok({ detail: 'CSRF Failed' }, 403),
    )

    await expect(api.joinRoom(1)).rejects.toThrow('CSRF Failed')
    const calls = fetchMock.mock.calls.map(([url]) => url)
    expect(calls.filter((url) => url === '/api/rooms/1/join/')).toHaveLength(2)
  })

  it('returns null for 204 responses', async () => {
    await loadApi('csrftoken=tok')
    fetchMock.mockResolvedValue(ok({}, 204))

    await expect(api.logout()).resolves.toBeNull()
  })

  it('prefers the response detail message in errors', async () => {
    await loadApi('csrftoken=tok')
    fetchMock.mockImplementation((url) =>
      url === '/api/auth/csrf/' ? ok({ csrfToken: 'fresh' }) : ok({ detail: 'Not allowed.' }, 403),
    )

    await expect(api.updateMemberRole(1, 2, 'OWNER')).rejects.toThrow('Not allowed.')
  })

  it('does not set a JSON content type for FormData bodies', async () => {
    await loadApi('csrftoken=tok')
    fetchMock.mockResolvedValue(ok({ user: { username: 'a' } }))

    const form = new FormData()
    form.append('avatar', new Blob(['x'], { type: 'image/png' }), 'a.png')
    await api.updateMe(form)

    const [, opts] = fetchMock.mock.calls[0]
    expect(opts.headers['Content-Type']).toBeUndefined()
    expect(opts.body).toBeInstanceOf(FormData)
  })
})