import marimo

__generated_with = "0.13.15"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import attoworld as aw
    import matplotlib.pyplot as plt
    import scipy
    import timeit
    aw.plot.set_style('light', font_size=14)
    return aw, mo, np, plt, scipy, timeit


@app.cell
def _(mo):
    mo.md(r"""## Check convergence of numerical derivatives""")
    return


@app.cell
def _(aw, np, plt):
    def convergence_check(order, N_pts):
        x = np.linspace(0.0, 2*np.pi, N_pts+1)[0:-1]
        dx = x[1]-x[0]
        y = np.cos(x)
        y_derivative_analytic = -np.sin(x)
        y_derivative = aw.numeric.derivative(y,1,order)/dx
        #y_derivative = aw.numeric.derivative_periodic(y,1,order)/dx
        return np.max(np.abs(y_derivative - y_derivative_analytic))

    N_pts_range = [16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512]
    order_range = range(1,6)

    convergence_data = np.array([[convergence_check(_order, _n) for _n in N_pts_range] for _order in order_range])

    lines = plt.loglog(N_pts_range,convergence_data.T)
    for order, line in zip(order_range, lines):
        line.set_label(f"{order}")
    plt.xlabel("Number of grid points")
    plt.ylabel("Mean error")
    plt.ylim(1e-15, 0.1)
    plt.legend()
    aw.plot.showmo()
    return (N_pts_range,)


@app.cell
def _(mo):
    mo.md(
        r"""
    ## Check interpolate()
    The interpolate function uses Fornberg's algorithm to generate interpolation stencils. It should have performance and accuracy similar to scipy's CubicSpline when neighbors=3. It will be comparatively slower if you would have reused the same CubicSpline object for multiple interpolations, however.
    """
    )
    return


@app.cell
def _(aw, np, plt, scipy):
    def plot_interpolate_test():
        def test_function(_x):
            beta = 11.0
            return np.sin(_x**2/beta)
        x = np.real(np.linspace(0.0,16.0,64))
        x_fine = np.real(np.linspace(0.0,16.0,512))
        x2 = np.linspace(0.01,15.99,333)
        y = test_function(x)
        y_fine = test_function(x_fine)
        y2 = test_function(x2)

        interpolated_rs = aw.numeric.interpolate(x2, x, y, neighbors=3)
        interpolated_scipy = scipy.interpolate.CubicSpline(x,y)(x2)

        fig,ax = plt.subplots(2,1, figsize=(6,6))
        ax[0].plot(x2, interpolated_rs, label="aw.numeric.interpolate")
        ax[0].plot(x2,interpolated_scipy,'--',label="scipy.interpolate.CubicSpline")
        ax[0].plot(x,y,'.', label="Input data")
        ax[0].set_xlabel("x")
        ax[0].set_ylabel("y")
        ax[0].legend(loc='lower left')
        aw.plot.label_letter('a',axis=ax[0])
        ax[1].semilogy(x2, np.abs(y2 - interpolated_rs),label="aw.numeric.interpolate")
        ax[1].plot(x2, np.abs(y2 - interpolated_scipy),label="scipy.interpolate.CubicSpline")
        ax[1].set_xlabel("x")
        ax[1].set_ylabel("Error")
        ax[1].legend()
        aw.plot.label_letter('b',axis=ax[1])

    plot_interpolate_test()
    aw.plot.showmo()
    return


@app.cell
def _(aw, np, scipy, timeit):
    def benchmark_interpolations():
        beta = 9.0
        x = np.real(np.linspace(0.0,16.0,333))
        x2 = np.linspace(0.1,15.99,2222)
        y = np.sin(x**2/beta)
        y2 = np.sin(x2**2/beta)
        print(f"aw.numeric.interpolate: {timeit.timeit(lambda: aw.numeric.interpolate(x2, x, y, neighbors=3), number=10000)} seconds")
        print(f"scipy.interpolate.CubicSpline: {timeit.timeit(lambda: scipy.interpolate.CubicSpline(x,y, extrapolate=False)(x2), number=10000)} seconds")

    benchmark_interpolations()
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ## Check FWHM error
    Note that the aw.numeric.fwhm() function has a much smaller error than the implementation I've seen elsewhere (which only reduces in error linearly with step size).
    """
    )
    return


@app.cell
def _(N_pts_range, aw, np, plt):
    def plot_fwhm_convergence():
        true_fwhm = 2*np.sqrt(2.0 * np.log(2.0))
        fwhm = []
        fwhm_th = []
        dx_array = []
        def old_fwhm(y, x):
            i_max = np.argmax(y)
            hm = y[i_max] / 2
            return (np.max(x[np.argwhere(y >= hm)]) - np.min(x[np.argwhere(y >= hm)]))

        for i in range(len(N_pts_range)):
            x = np.linspace(-5, 5, N_pts_range[i])
            dx = x[1]-x[0]
            y = np.exp(-x**2/2)
            fwhm.append(aw.attoworld_rs.fwhm(y, dx,neighbors=2))
            fwhm_th.append(old_fwhm(y,x))
            dx_array.append(dx)
        plt.loglog(N_pts_range, dx_array, label="time step")
        plt.loglog(N_pts_range, np.abs(fwhm-true_fwhm), label="FWHM in attoworld.numeric")
        plt.loglog(N_pts_range, np.abs(fwhm_th-true_fwhm), label="index-based FWHM")
        plt.xlabel("# of points")
        plt.ylabel("Error")
        plt.legend()


    plot_fwhm_convergence()
    aw.plot.showmo()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
