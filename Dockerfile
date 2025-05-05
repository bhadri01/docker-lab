FROM dockerbase:latest

ARG USERNAME
ENV USERNAME=${USERNAME}

# Add user and perform other operations
# Create group with GID 1001 if it does not exist, add user, set password, and add to sudo group
RUN if ! getent group 1001; then groupadd -g 1001 ${USERNAME}; fi && \
    adduser --uid 1001 --gid 1001 ${USERNAME} --gecos "" --disabled-password --force-badname && \
    echo "${USERNAME}:${USERNAME}@321" | chpasswd && \
    usermod -aG sudo ${USERNAME}

# Make use of stopsignal (instead of sigterm) to stop systemd containers
STOPSIGNAL SIGRTMIN+3

ENV USERNAME=${USERNAME}

COPY wg0.conf /etc/wireguard/
# Set systemd as entrypoint
CMD ["/setup.sh"]

#./docker-build --name hari --instance docker --no-cache
