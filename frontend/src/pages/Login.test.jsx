import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

const { loginMock } = vi.hoisted(() => ({ loginMock: vi.fn() }))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: null, login: loginMock }),
}))

import { Login } from './Login.jsx'

describe('Login', () => {
  it('submits credentials through the auth context', async () => {
    loginMock.mockResolvedValue({ username: 'alice' })
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText('Username'), 'alice')
    await user.type(screen.getByLabelText('Password'), 's3cret!')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(loginMock).toHaveBeenCalledWith({ username: 'alice', password: 's3cret!' })
  })

  it('shows the error message when login fails', async () => {
    loginMock.mockRejectedValue(new Error('Invalid credentials.'))
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText('Username'), 'alice')
    await user.type(screen.getByLabelText('Password'), 'wrong')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText('Invalid credentials.')).toBeInTheDocument()
  })

  it('does not submit when fields are empty', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: /sign in/i }))
    expect(loginMock).not.toHaveBeenCalled()
  })
})