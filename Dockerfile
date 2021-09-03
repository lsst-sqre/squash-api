# This Dockerfile has four stages:
#
# base-image
#   Updates the base Python image with security patches and common system
#   packages. This image becomes the base of all other images.
# dependencies-image
#   Installs third-party dependencies (requirements/main.txt) into a virtual
#   environment. This virtual environment is ideal for copying across build
#   stages.
# install-image
#   Installs the app into the virtual environment.
# runtime-image
#   - Copies the virtual environment into place.
#   - Runs a non-root user.
#   - Sets up the entrypoint and port.

FROM python:3.9.2-buster AS base-image
LABEL maintainer "afausti@lsst.org"

# Update system packages
COPY scripts/install-base-packages.sh .
RUN ./install-base-packages.sh

FROM base-image AS dependencies-image

# Create a Python virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
# Make sure we use the virtualenv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
# Put the latest pip and setuptools in the virtualenv
RUN pip install --upgrade --no-cache-dir pip setuptools wheel

# Install the app's Python runtime dependencies
COPY requirements/main.txt ./requirements.txt
RUN pip install --quiet --no-cache-dir -r requirements.txt

FROM base-image AS install-image

# Use the virtualenv
COPY --from=dependencies-image /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . /app
WORKDIR /app

RUN pip install --no-cache-dir .

FROM base-image AS runtime-image

# Create a non-root user
RUN groupadd -r uwsgi_grp && useradd -r -g uwsgi_grp --create-home uwsgi
WORKDIR /home/uwsgi

# Make sure we use the virtualenv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the virtualenv
COPY --from=install-image /opt/venv /opt/venv

# Copy initialization script (used with docker-compose)
COPY scripts/wait-for-it.sh ./

# Copy uwsgi configuration file
COPY uwsgi.ini ./

# Switch to non-root user
USER uwsgi

EXPOSE 5000

ENTRYPOINT ["uwsgi", "uwsgi.ini"]
