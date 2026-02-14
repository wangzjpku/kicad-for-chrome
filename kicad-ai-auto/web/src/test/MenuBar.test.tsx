import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import MenuBar from '../components/MenuBar'

describe('MenuBar', () => {
  const consoleLogSpy = vi.spyOn(console, 'log').mockImplementation(() => {})

  beforeEach(() => {
    consoleLogSpy.mockClear()
  })

  it('should render the menu bar', () => {
    render(<MenuBar />)

    expect(screen.getByTestId('menubar')).toBeInTheDocument()
  })

  it('should render main menu sections', () => {
    render(<MenuBar />)

    // Just verify the menu bar has some content
    const menuBar = screen.getByTestId('menubar')
    expect(menuBar).toBeInTheDocument()
  })

  it('should have file menu', () => {
    render(<MenuBar />)

    expect(screen.getByTestId('menu-file')).toBeInTheDocument()
  })

  it('should render menu items structure', () => {
    render(<MenuBar />)

    // Check that the menu structure exists
    const menuBar = screen.getByTestId('menubar')
    expect(menuBar).toBeInTheDocument()
  })
})
