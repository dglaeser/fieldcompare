"""
Solve a Poisson problem with FEniCSX
and do a regression test with fieldcompare

If you don't have FEniCSX installed but you
have a working Docker installation you can simply
run `run_with_fenics_in_docker.sh fenics_poisson.py`
"""
import numpy as np

import ufl

from dolfinx import fem, io, mesh
from ufl import dx, grad, inner

from mpi4py import MPI
from petsc4py.PETSc import ScalarType

from fieldcompare.io import read
from fieldcompare.mesh import MeshFieldsComparator

# create mesh
msh = mesh.create_rectangle(
    comm=MPI.COMM_WORLD,
    points=((0.0, 0.0), (1.0, 1.0)),
    n=(10, 10),
    cell_type=mesh.CellType.triangle,
)

# and boundary markers
def boundary_marker(x):
    return np.logical_or.reduce(
        (
            np.isclose(x[0], 0.0),
            np.isclose(x[0], 1.0),
            np.isclose(x[1], 0.0),
            np.isclose(x[1], 1.0),
        )
    )


# incorporate Dirichlet BC into space
V = fem.FunctionSpace(msh, ("Lagrange", 1))
facets = mesh.locate_entities_boundary(msh, dim=1, marker=boundary_marker)
dirichlet_dofs = fem.locate_dofs_topological(V=V, entity_dim=1, entities=facets)
bc = fem.dirichletbc(value=ScalarType(0), dofs=dirichlet_dofs, V=V)

# solve Poisson problem
print("\nSolving Poisson problem...")
u, v = ufl.TrialFunction(V), ufl.TestFunction(V)
f = 1.0
sol = problem = fem.petsc.LinearProblem(
    inner(grad(u), grad(v)) * dx,
    inner(f, v) * dx,
    bcs=[
        bc,
    ],
).solve()

# write output
print("Writing output...")
with io.XDMFFile(msh.comm, "poisson.xdmf", "w") as file:
    file.write_mesh(msh)
    file.write_function(sol)

# do a regression test against a reference solution
# using two different mesh file formats as a demonstration,
# of course, using the same mesh formats is also possible
print("Comparing output against reference...")
source = read("poisson.xdmf")
reference = read("poisson-reference.pvd")

# dolfinx writes time series
if source.number_of_steps != reference.number_of_steps:
    raise RuntimeError("Time series does not have the same amount of steps!")

# compare all time steps (here it is just one)
for idx, (source_step, ref_step) in enumerate(zip(source, reference)):
    print(f"Comparing step {idx} of {source.number_of_steps}\n")
    result = MeshFieldsComparator(source=source_step, reference=ref_step)()
    print(f"Test summary: {result.status} ({result.report})")
    if not result:
        raise RuntimeError("Comparison failed!")
